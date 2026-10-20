"""Diagnostic-only Jac dispatch/worker profiler; source/app files stay intact.

Launch this interpreter with PYTHONPATH pointing at the intended Jac source.
A sequential diagnostic client sends100 warm and100 profiled writes per route.
SIGTERM/SIGINT flush accumulated artifacts; no profiling files are emitted
inside a measured request. Mode spans avoids cProfile for lighter wall/CPU spans.
"""
import argparse
import asyncio
from collections import defaultdict
import contextvars
import cProfile
import functools
import inspect
import json
import os
from pathlib import Path
import pstats
import signal
import sys
import threading
import time

CURRENT=contextvars.ContextVar('jac_diagnostic_request',default=None)
MAIN_PROFILE=contextvars.ContextVar('jac_diagnostic_main_profile',default=None)
PROFILES=defaultdict(list)
ROWS=[]
COUNTS=defaultdict(int)
PATCHES=[]
LOCK=threading.Lock()
ACTIVE=0
DUMPED=False


def identity(fn):
    return getattr(fn,'__qualname__',getattr(fn,'__name__',type(fn).__name__))


def profile():
    return cProfile.Profile(timer=time.thread_time)


def span_finish(rec,label,wall,cpu,category=None):
    rec['spans'].append({'name':label,'thread_ident':threading.get_ident(),
                         'wall_ms':1000*(time.perf_counter()-wall),
                         'thread_cpu_ms':1000*(time.thread_time()-cpu),
                         **({'sql_category':category} if category else {})})


def sql_category(sql):
    text=' '.join(str(sql).upper().split())
    verb=text.split(' ',1)[0] if text else 'EMPTY'
    if verb in ('BEGIN','COMMIT','ROLLBACK','SET','SHOW','SAVEPOINT','RELEASE'):return verb.lower()
    if verb in ('CREATE','ALTER','DROP','TRUNCATE'):return 'ddl-'+verb.lower()
    if 'INSERT INTO GRAPH_TYPES' in text:return 'type-registry-write'
    if 'SELECT TYPE_NAME FROM GRAPH_TYPES' in text and 'JOIN' not in text:return 'type-registry-read'
    if 'IDENTITY_' in text or 'SSO_' in text:return 'identity'
    if verb in ('INSERT','UPDATE','DELETE'):
        return ('anchor-write' if 'ANCHORS' in text else 'mirror-write' if 'G_N_' in text or 'G_E_' in text else 'other-write')+'-'+verb.lower()
    if 'FOR UPDATE' in text:return 'optimistic-concurrency-check'
    if verb=='SELECT' and 'UNNEST(' in text and 'JOIN ANCHORS' in text:return 'anchor-traversal'
    if 'FROM ANCHORS' in text or 'JOIN ANCHORS' in text:
        if 'JOIN ANCHORS' in text or 'UNNEST(' in text:return 'anchor-traversal'
        return 'anchor-load'
    if 'G_N_' in text or 'G_E_' in text:return 'mirror-read'
    if 'PG_' in text or 'INFORMATION_SCHEMA' in text:return 'schema-check'
    return 'other-'+verb.lower()


def wrap_span(fn,label):
    if inspect.iscoroutinefunction(fn):
        @functools.wraps(fn)
        async def wrapped(*args,**kwargs):
            rec=CURRENT.get()
            if rec is None:return await fn(*args,**kwargs)
            wall=time.perf_counter();cpu=time.thread_time()
            try:return await fn(*args,**kwargs)
            finally:span_finish(rec,label,wall,cpu,sql_category(args[1] if len(args)>1 else kwargs.get("sql","")) if label=="PgStore._run" else None)
    else:
        @functools.wraps(fn)
        def wrapped(*args,**kwargs):
            rec=CURRENT.get()
            if rec is None:return fn(*args,**kwargs)
            wall=time.perf_counter();cpu=time.thread_time()
            try:return fn(*args,**kwargs)
            finally:span_finish(rec,label,wall,cpu,sql_category(args[1] if len(args)>1 else kwargs.get("sql","")) if label=="PgStore._run" else None)
    return wrapped


def patch_method(cls,name,label):
    if not hasattr(cls,name):return
    descriptor=inspect.getattr_static(cls,name)
    original=descriptor.__func__ if isinstance(descriptor,(staticmethod,classmethod)) else descriptor
    wrapped=wrap_span(original,label)
    if isinstance(descriptor,staticmethod):wrapped=staticmethod(wrapped)
    elif isinstance(descriptor,classmethod):wrapped=classmethod(wrapped)
    setattr(cls,name,wrapped);PATCHES.append(label)


def node_id(key):return f'{key[0]}:{key[1]}:{key[2]}'


def export_stats(stats,target):
    nodes=[];edges=[]
    for key,(primitive,total,exclusive,cumulative,callers) in stats.stats.items():
        nodes.append({'id':node_id(key),'file':key[0],'line':key[1],'function':key[2],
                      'primitive_calls':primitive,'total_calls':total,
                      'exclusive_cpu_ms':1000*exclusive,'cumulative_cpu_ms':1000*cumulative})
        for caller,details in callers.items():
            edge={'caller':node_id(caller),'callee':node_id(key)}
            if isinstance(details,tuple):
                edge.update(primitive_calls=details[0],total_calls=details[1],
                            exclusive_cpu_ms=1000*details[2],cumulative_cpu_ms=1000*details[3])
            else:edge['calls']=details
            edges.append(edge)
    result={'timer':'time.thread_time CPU seconds','total_profiled_cpu_ms':1000*stats.total_tt,
            'top_exclusive':sorted(nodes,key=lambda item:-item['exclusive_cpu_ms'])[:100],
            'top_cumulative':sorted(nodes,key=lambda item:-item['cumulative_cpu_ms'])[:100],
            'nodes':nodes,'call_edges':edges}
    target.write_text(json.dumps(result,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',required=True,type=Path)
    parser.add_argument('--mode',choices=['cprofile','spans','both'],default='both')
    parser.add_argument('--operations',default='create_tweet,follow_user,like_tweet')
    parser.add_argument('--warmups',type=int,default=100)
    parser.add_argument('--limit',type=int,default=100)
    parser.add_argument('jac_args',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    command=args.jac_args[1:] if args.jac_args[:1]==['--'] else args.jac_args
    if not command:parser.error('Supply Jac CLI arguments after --, e.g. -- start main.jac -p18120 --no-client')
    out=args.output_dir.resolve()
    if out.exists():raise RuntimeError(f'Refusing to overwrite {out}')
    out.mkdir(parents=True)
    operations=set(args.operations.split(','))
    enabled_profile=args.mode in ('cprofile','both')
    enabled_spans=args.mode in ('spans','both')
    import jaclang
    from jaclang.runtimelib.serving.app import ServingApp
    from jaclang.runtimelib.server import ExecutionManager
    from jaclang.runtimelib.session import Session
    from jaclang.runtimelib.store import PgStore
    from jaclang.runtimelib.serializer import Serializer
    from jaclang.jac0core import runtime
    selected_source=jaclang.__file__

    def dump():
        global DUMPED
        if DUMPED:return
        DUMPED=True
        for (operation,lane),profiles in PROFILES.items():
            if not profiles:continue
            stats=pstats.Stats(profiles[0])
            for prof in profiles[1:]:stats.add(prof)
            prefix=out/f'{operation}.{lane}'
            stats.dump_stats(str(prefix)+'.pstats')
            export_stats(stats,Path(str(prefix)+'.json'))
            with Path(str(prefix)+'.txt').open('w') as handle:
                stats.stream=handle;stats.sort_stats('tottime').print_stats(60)
                stats.sort_stats('cumulative').print_stats(60)
        (out/'requests.json').write_text(json.dumps(ROWS,indent=2))
        grouped={}
        for rec in ROWS:
            for item in rec['spans']:
                key=f"{rec['operation']}|{item['name']}|thread{item['thread_ident']}"
                value=grouped.setdefault(key,{'count':0,'wall_ms':0.,'thread_cpu_ms':0.})
                value['count']+=1;value['wall_ms']+=item['wall_ms'];value['thread_cpu_ms']+=item['thread_cpu_ms']
        (out/'span-summary.json').write_text(json.dumps(grouped,indent=2))
        (out/'metadata.json').write_text(json.dumps({'source':selected_source,'pid':os.getpid(),
            'python':sys.version,'mode':args.mode,'warmups_per_route':args.warmups,'profile_limit_per_route':args.limit,
            'route_counts':dict(COUNTS),'profiled_requests':len(ROWS),'patches':PATCHES,
            'timer':'cProfile time.thread_time excludes thread waiting; selected spans record wall and thread CPU separately',
            'scope':'Main profile spans ServingApp.dispatch through response construction including routing/auth/root/deserialization/commit/serialization; HTTP socket output follows dispatch. Main profiling pauses across asyncio.to_thread while the worker owns the Python 3.14 global monitoring slot, and resumes afterward. Worker profiles cover asyncio.to_thread calls and retain callable names. Sequential client required: other main-loop work during awaits can also be charged to the main profiler.',
            'interpretation':'Profiles are diagnostic and add overhead. Main/worker profiles are separate. Cumulative function/span times are nested; do not add them. Whole server headline differs between Jac and SQL handlers; preserve outer request scope and original timing headers.'},indent=2))
        print('Diagnostic profiles saved:',out,flush=True)

    import atexit
    atexit.register(dump)
    def stop(signum,frame):
        dump();raise SystemExit(128+signum)
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)

    original_to_thread=asyncio.to_thread
    async def to_thread(func,*pos,**kw):
        rec=CURRENT.get()
        if rec is None:return await original_to_thread(func,*pos,**kw)
        name=identity(func)
        def invoke():
            profiler=profile() if enabled_profile else None
            wall=time.perf_counter();cpu=time.thread_time()
            if profiler:profiler.enable()
            try:return func(*pos,**kw)
            finally:
                if profiler:
                    profiler.disable()
                    lane='worker-walker' if 'spawn' in name.lower() else 'worker-aux'
                    with LOCK:PROFILES[(rec['operation'],lane)].append(profiler)
                span_finish(rec,'asyncio.to_thread:'+name,wall,cpu)
        # Python 3.14 cProfile reserves one process-global monitoring tool ID.
        # Release the main profiler while the worker owns it, then resume.
        main_profiler=MAIN_PROFILE.get()
        if main_profiler:main_profiler.disable()
        try:return await original_to_thread(invoke)
        finally:
            if main_profiler:main_profiler.enable()
    asyncio.to_thread=to_thread

    if enabled_spans:
        globals_=ExecutionManager.spawn_walker_sync.__globals__
        for name in ['_run_function_with_occ','_abegin_user_request_context','_begin_request_context','_deserialize_wire_args']:
            if callable(globals_.get(name)):
                globals_[name]=wrap_span(globals_[name],name);PATCHES.append(name)
        seen_globals=set()
        for method_name in ['__init__','__new__','commit','batch_get']:
            method=getattr(Session,method_name,None)
            session_globals=getattr(method,'__globals__',None)
            if session_globals is None or id(session_globals) in seen_globals:continue
            seen_globals.add(id(session_globals))
            for name in ['_toml_section','promotions_for','retention_days_for']:
                if callable(session_globals.get(name)):
                    session_globals[name]=wrap_span(session_globals[name],'session.'+name)
                    PATCHES.append('session.'+name)
        for cls,names in [(Session,['flush','_flush_locked','commit','mark_dirty','batch_get','read_barrier']),
                          (PgStore,['_run','commit','begin','upsert','load_full']),
                          (Serializer,['serialize','deserialize']),
                          (ExecutionManager,['_finalize_call_response'])]:
            for name in names:patch_method(cls,name,cls.__name__+'.'+name)
        graph=getattr(runtime,'JacGraph',None)
        if graph:
            for name in ['connect','build_edge','disconnect']:patch_method(graph,name,'JacGraph.'+name)

    original_dispatch=ServingApp.dispatch
    @functools.wraps(original_dispatch)
    async def dispatch(self,request):
        global ACTIVE
        path=request.url.path
        operation=path.rsplit('/',1)[-1] if path.startswith('/walker/') else ''
        if operation not in operations:return await original_dispatch(self,request)
        COUNTS[operation]+=1
        ordinal=COUNTS[operation]
        if ordinal<=args.warmups or ordinal>args.warmups+args.limit:
            return await original_dispatch(self,request)
        if ACTIVE:raise RuntimeError('Diagnostic profiler requires one sequential request at a time')
        ACTIVE+=1
        rec={'operation':operation,'ordinal':ordinal,'main_thread_ident':threading.get_ident(),
             'start_wall_unix':time.time(),'spans':[]}
        token=CURRENT.set(rec);profiler=profile() if enabled_profile else None
        profile_token=MAIN_PROFILE.set(profiler)
        wall=time.perf_counter();cpu=time.thread_time()
        if profiler:profiler.enable()
        try:
            response=await original_dispatch(self,request)
            rec['response_status']=getattr(response,'status_code',None)
            return response
        finally:
            if profiler:
                profiler.disable();PROFILES[(operation,'main-dispatch')].append(profiler)
            rec.update(wall_ms=1000*(time.perf_counter()-wall),main_thread_cpu_ms=1000*(time.thread_time()-cpu))
            rec['worker_thread_cpu_ms']=sum(span['thread_cpu_ms'] for span in rec['spans'] if span['name'].startswith('asyncio.to_thread:'))
            rec['main_plus_worker_cpu_ms']=rec['main_thread_cpu_ms']+rec['worker_thread_cpu_ms']
            ROWS.append(rec);MAIN_PROFILE.reset(profile_token);CURRENT.reset(token);ACTIVE-=1
    ServingApp.dispatch=dispatch
    (out/'ready.json').write_text(json.dumps({'pid':os.getpid(),'source':selected_source,'mode':args.mode,'operations':sorted(operations)},indent=2))
    sys.argv=['jac',*command]
    from jaclang.jac0core.cli_boot import start_cli
    start_cli()


if __name__=='__main__':main()

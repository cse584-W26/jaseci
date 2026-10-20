import subprocess,pathlib,json,sys
R=pathlib.Path(__file__).resolve().parent;o=R/'timing/delay2100us';o.mkdir(parents=True,exist_ok=False);base=['docker','run','--rm','--cpuset-cpus','9,19','--network','container:jac-webridge-mysql57','--cap-add','NET_ADMIN','jac-webridge-network:ubuntu22']
def run(name,cmd,check=True):
 (o/(name+'-command.json')).write_text(json.dumps(cmd));r=subprocess.run(cmd,capture_output=True,text=True);(o/(name+'.stdout')).write_text(r.stdout);(o/(name+'.stderr')).write_text(r.stderr);assert not check or r.returncode==0,(name,r.returncode,r.stderr);return r
before=run('qdisc-before',base+['tc','-j','qdisc','show','dev','eth0']);old=json.loads(before.stdout);assert len(old)==1 and old[0]['kind']=='noqueue',old
ip=subprocess.check_output(['docker','inspect','-f','{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}','jac-webridge-mysql57'],text=True).strip();ping=['docker','run','--rm','--cpuset-cpus','9,19','--network','host','jac-webridge-network:ubuntu22','ping','-c','10','-i','0.2',ip];run('ping-before',ping)
try:
 run('set-delay',base+['tc','qdisc','replace','dev','eth0','root','netem','delay','2100us']);run('qdisc-delay',base+['tc','-s','qdisc','show','dev','eth0']);run('ping-delay',ping)
 for variant in ['full','pruned']:
  run('timing-'+variant,[sys.executable,str(R/'warm_timing.py'),'--variant',variant,'--db','jac_alignment_utf8','--out',str(o/variant),'--warm','10','--measure','30'])
finally:
 run('restore-qdisc',base+['tc','qdisc','del','dev','eth0','root']);run('qdisc-after',base+['tc','-j','qdisc','show','dev','eth0']);run('ping-after',ping);(o/'restored.json').write_text(json.dumps({'restored_to_initial_noqueue':True,'database_container':'jac-webridge-mysql57','delay_scope':'Only dedicated database network namespace egress','specified_delay_us':2100},indent=2))
print(o)

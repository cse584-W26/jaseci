"""Build an isolated SELECT-frontend overlay; original artifact source is unchanged."""
from pathlib import Path
import hashlib,json,difflib
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[3]
source=BASE/'webridge/SourceCode/webridge-common/basic-components/src/main/java/webridge/wbridge/sql/ast/SQLAstVisitor.java'
s=source.read_text();old=s
start=s.index('  @Override\n  public void endVisit(MySqlSelectQueryBlock x)')
end=s.index('  private void handleLimit(',start)
s=s[:start]+'''  @Override
  public void endVisit(MySqlSelectQueryBlock x) {
    // Schema resolution still visits every nested scope. Result columns and
    // parameters are registered once at the top-level SELECT statement.
    sqlType = SqlType.SELECT;
    super.endVisit(x);
  }

''' +s[end:]
start=s.index('  @Override\n  public void endVisit(SQLSelectStatement selectStatement)')
end=s.index('  public String getColumnType(',start)
new=(HERE/'select_extension.java.fragment').read_text()
s=s[:start]+new+'\n'+s[end:]
p=HERE/'src/webridge/wbridge/sql/ast/SQLAstVisitor.java';p.write_text(s)
(HERE/'overlay.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile=str(source),tofile=str(p))))
(HERE/'provenance.json').write_text(json.dumps({'original':str(source),'original_sha256':hashlib.sha256(old.encode()).hexdigest(),'overlay_sha256':hashlib.sha256(s.encode()).hexdigest(),'scope':'SELECT result-scope and typed parameter metadata only; original SQL and non-SELECT handling preserved'},indent=2))

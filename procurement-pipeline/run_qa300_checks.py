"""Run focused new and baseline suites and save their actual results."""
import io
import unittest
import build_qa300 as x


def main():
    modules=['test_company_master','test_c01_documents','test_remaining_companies','test_qa300']
    reports=[];log=[]
    for module in modules:
        stream=io.StringIO();suite=unittest.defaultTestLoader.loadTestsFromName(module)
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
        log.append(stream.getvalue())
        reports.append(dict(module=module,tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),passed=result.wasSuccessful()))
    x.write(x.ROOT/'validation/test_results.json',dict(version=x.VERSION,suites=reports,total=sum(s['tests_run'] for s in reports),
      status='passed' if all(s['passed'] for s in reports) else 'failed',
      scope='파일·스키마·권한·산식·날짜·오류 주입·회귀 테스트; 실제 RAG/LLM 성능 아님'))
    (x.ROOT/'validation/test_output.txt').write_text('\n'.join(log),encoding='utf-8')
    print(*[f"{s['module']}: {s['tests_run']} / {'passed' if s['passed'] else 'failed'}" for s in reports],sep='\n')
    if not all(s['passed'] for s in reports):raise SystemExit(1)


if __name__=='__main__':main()

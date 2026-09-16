import unittest
import rag_pilot_calculation as c

class CalculationTests(unittest.TestCase):
    def table(self,**changes):
        values={'통화':'KRW','VAT 기준':'exclusive — VAT 제외','VAT 가정 요율':'10 percent · 합성 설정값',
        'scoped_direct_net':'100','synthetic_external_net':'0','original_agreement_gross':'110',
        'overhead_percent':'10','contingency_percent':'10','margin_percent':'20','산식':c.FORMULA,
        'target_net':'999999','target_gross':'888888'}
        values.update(changes)
        return '## calculation\n\n'+'\n'.join(f'| calculation / {k} | {v} |' for k,v in values.items())
    def test_margin_is_revenue_fraction_and_gross_input_unvat(self):
        result=c.calculation_note(self.table())
        self.assertIn('공급가 VAT 제외 300원',result)
        self.assertIn('VAT 포함 330원',result)
        self.assertNotIn('999999',result)
        self.assertNotIn('888888',result)
    def test_optional_agreement_not_real_zero(self):
        result=c.calculation_note(self.table(original_agreement_gross='null — 미설정'))
        self.assertIn('실제 금액이 0이라는 뜻 아님',result)
        self.assertIn('공급가 VAT 제외 150원',result)
    def test_missing_required_value_fails_closed(self):
        self.assertIsNone(c.calculation_note(self.table(scoped_direct_net='null')))
    def test_invalid_margin_fails_closed(self):
        self.assertIsNone(c.calculation_note(self.table(margin_percent='100')))
    def test_unrecognized_formula_fails_closed(self):
        self.assertIsNone(c.calculation_note(self.table(**{'산식':'use expected answer'})))
    def test_duplicate_input_fails_closed(self):
        self.assertIsNone(c.calculation_note(self.table()+'\n| calculation / margin_percent | 30 |'))
    def test_only_final_rounding(self):
        result=c.calculation_note(self.table(scoped_direct_net='1',original_agreement_gross='null — 미설정',overhead_percent='0',contingency_percent='0'))
        self.assertIn('공급가 VAT 제외 1원',result)
        self.assertIn('VAT 포함 1원',result)

if __name__=='__main__':unittest.main()

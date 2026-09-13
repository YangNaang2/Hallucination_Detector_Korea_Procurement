import unittest
import rag_pilot_routing as r


def chunk(text, level='L1', scenario=None):
    return dict(text=text, security_level=level, scenario_id=scenario)


class ScopedRoutingTests(unittest.TestCase):
    def test_ocr_license_requires_both_subjects(self):
        cs = [chunk('일체 사용권 및 라이센스 비용'), chunk('OCR 변환 기능'),
              chunk('AI OCR 솔루션 라이선스 구매')]
        self.assertEqual(r.specific_public('OCR 사용권을 구독으로 계획?', cs, [0, 1, 2]), [2])

    def test_recovery_requires_joint_time_clause(self):
        cs = [chunk('방문자 관리, 복구 개요'), chunk('장애 3시간 이내 방문, 7시간 이내 복구')]
        self.assertEqual(r.specific_public('방문과 복구 시간을 구분?', cs, [0, 1]), [1])

    def test_digitization_units_not_budget_units(self):
        cs = [chunk('예산 단위 관리'), chunk('종이 123,456면 전자화')]
        self.assertEqual(r.specific_public('전자화 물량 단위?', cs, [0, 1]), [1])
        self.assertEqual(r.specific_public('예산 단위?', cs, [0, 1]), [])

    def test_short_id_does_not_match_different_person(self):
        cs = [chunk('## C02-P-01', 'L2'), chunk('## C02-P-09', 'L2')]
        self.assertEqual(r.named_entities('P-09를 배치?', cs, [0, 1]), [1])
        self.assertEqual(r.named_entities('C03-P-09를 배치?', cs, [0, 1]), [])

    def test_scenario_plan_not_master_or_other_scenario(self):
        cs = [chunk('## availability', 'L2'), chunk('## staffing-1', 'L2', 'other'),
              chunk('## staffing-1', 'L2', 'current')]
        self.assertEqual(r.scenario_sections('부분월 공수', 'current', cs, [0, 1, 2]), [2])
        self.assertEqual(r.scenario_sections('마진 가격', 'current', cs, [0, 1, 2]), [])

    def test_expiry_uses_scenario_state_change(self):
        cs = [chunk('## certificate', 'L2'), chunk('## state_change', 'L2', 'current')]
        self.assertEqual(r.scenario_sections('합성 인증 종료 후 유효?', 'current', cs, [0, 1]), [1])


if __name__ == '__main__':
    unittest.main()

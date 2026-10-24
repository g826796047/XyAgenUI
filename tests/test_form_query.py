import unittest


class FormContractTests(unittest.TestCase):
    def test_forms_use_standard_text_input_and_data_model(self):
        import json
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        text = (root / "examples/form-ingredients.jsonl").read_text(encoding="utf-8")
        self.assertIn('"component":"TextInput"', text)
        self.assertIn('"updateDataModel"', text)
        self.assertNotIn('"computed"', text)


if __name__ == "__main__":
    unittest.main()

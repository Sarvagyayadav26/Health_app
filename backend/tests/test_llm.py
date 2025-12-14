import unittest
from src.llm.client import LLMClient
from src.llm.prompts import create_prompt
from src.llm.instruction_templates import get_instruction_template

class TestLLMClient(unittest.TestCase):

    def setUp(self):
        self.llm_client = LLMClient()

    def test_generate_response(self):
        prompt = create_prompt("What is the capital of France?")
        response = self.llm_client.generate_response(prompt)
        self.assertIsInstance(response, str)
        self.assertNotEqual(response, "")

    def test_create_prompt(self):
        user_input = "Tell me about the solar system."
        prompt = create_prompt(user_input)
        self.assertIn(user_input, prompt)

    def test_get_instruction_template(self):
        template = get_instruction_template()
        self.assertIsInstance(template, str)
        self.assertNotEqual(template, "")

if __name__ == '__main__':
    unittest.main()
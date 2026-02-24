from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

class PrivacyGuard:
    def __init__(self):
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()

    def redact(self, text: str) -> str:
        """
        Redacts PII from the input text using Microsoft Presidio.
        """
        if not text:
            return text
            
        # Analyze the text for PII
        results = self.analyzer.analyze(text=text, language='en')
        
        # Define operators for redaction (e.g., replace with [ENTITY_TYPE])
        operators = {
            "PERSON": OperatorConfig("replace", {"new_value": "[PERSON]"}),
            "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[EMAIL]"}),
            "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "[PHONE]"}),
            "LOCATION": OperatorConfig("replace", {"new_value": "[LOCATION]"}),
            "CREDIT_CARD": OperatorConfig("replace", {"new_value": "[CARD]"}),
            "CRYPTO": OperatorConfig("replace", {"new_value": "[CRYPTO]"}),
            "IBAN_CODE": OperatorConfig("replace", {"new_value": "[IBAN]"}),
            "IP_ADDRESS": OperatorConfig("replace", {"new_value": "[IP]"}),
            "US_SSN": OperatorConfig("replace", {"new_value": "[SSN]"}),
        }
        
        # Anonymize the text
        anonymized_result = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=operators
        )
        
        return anonymized_result.text

if __name__ == "__main__":
    # Quick test
    guard = PrivacyGuard()
    sample_text = "My name is John Doe and my phone number is 212-555-0199. I live in Hanoi."
    redacted = guard.redact(sample_text)
    print(f"Original: {sample_text}")
    print(f"Redacted: {redacted}")

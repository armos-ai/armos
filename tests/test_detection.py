import pytest
from armos.detection.engine import DetectionEngine


@pytest.fixture(scope="module")
def engine():
    return DetectionEngine()


def test_detects_person_name(engine):
    entities = engine.detect("Please call John Smith immediately")
    assert any(e.entity_type == "NAME" for e in entities)

def test_detects_email(engine):
    entities = engine.detect("Send the report to john.smith@company.com")
    assert any(e.entity_type == "EMAIL" for e in entities)

def test_detects_indian_phone(engine):
    entities = engine.detect("Call me on +91 98765 43210")
    assert any(e.entity_type == "PHONE" for e in entities)

def test_detects_aadhaar_spaces(engine):
    entities = engine.detect("My Aadhaar is 2345 6789 0123")
    assert any(e.entity_type == "AADHAAR" for e in entities)

def test_detects_aadhaar_hyphens(engine):
    entities = engine.detect("UID: 2345-6789-0123")
    assert any(e.entity_type == "AADHAAR" for e in entities)

def test_detects_pan(engine):
    entities = engine.detect("PAN card: ABCDE1234F")
    assert any(e.entity_type == "PAN" for e in entities)

def test_detects_credit_card(engine):
    entities = engine.detect("Card: 4111 1111 1111 1111")
    assert any(e.entity_type == "CARD" for e in entities)

def test_detects_ip_address(engine):
    entities = engine.detect("Request from 192.168.1.100")
    assert any(e.entity_type == "IP" for e in entities)

def test_detects_openai_api_key(engine):
    entities = engine.detect("key is sk-abc123def456ghi789jkl012mno345pqr")
    assert any(e.entity_type == "APIKEY" for e in entities)

def test_detects_aws_key(engine):
    entities = engine.detect("AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE")
    assert any(e.entity_type == "APIKEY" for e in entities)

def test_detects_ssn(engine):
    entities = engine.detect("Employee SSN on file: 371-53-1234.")
    assert any(e.entity_type == "SSN" for e in entities)

def test_detects_iban(engine):
    entities = engine.detect("Please transfer to IBAN GB29NWBK60161331926819.")
    assert any(e.entity_type == "IBAN" for e in entities)

def test_no_false_positives(engine):
    entities = engine.detect("The weather in Bangalore is pleasant today.")
    assert len(entities) == 0

def test_empty_string(engine):
    assert engine.detect("") == []

def test_multiple_entities(engine):
    text = "Patient John Smith, Aadhaar 2345 6789 0123, email john@hospital.com"
    entities = engine.detect(text)
    assert len(entities) >= 3

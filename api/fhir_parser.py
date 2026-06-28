import json
import base64
from typing import Optional


def parse_fhir_bundle(fhir_json: dict) -> dict:
    """
    Parse a FHIR Bundle and extract clinical text.
    Works with raw dict — no strict validation.
    """
    try:
        clinical_text = []
        patient_info = {}

        entries = fhir_json.get("entry", [])

        for entry in entries:
            resource = entry.get("resource", {})
            resource_type = resource.get("resourceType", "")

            # Extract patient demographics
            if resource_type == "Patient":
                names = resource.get("name", [])
                if names:
                    name = names[0]
                    given = name.get("given", [""])[0]
                    family = name.get("family", "")
                    patient_info["name"] = f"{given} {family}".strip()
                if resource.get("birthDate"):
                    patient_info["dob"] = resource["birthDate"]

            # Extract conditions
            elif resource_type == "Condition":
                code = resource.get("code", {})
                if code.get("text"):
                    clinical_text.append(code["text"])
                elif code.get("coding"):
                    display = code["coding"][0].get("display", "")
                    if display:
                        clinical_text.append(display)

            # Extract clinical notes
            elif resource_type == "DocumentReference":
                contents = resource.get("content", [])
                for content in contents:
                    attachment = content.get("attachment", {})
                    data = attachment.get("data", "")
                    if data:
                        decoded = base64.b64decode(data).decode("utf-8")
                        clinical_text.append(decoded)

            # Extract observations
            elif resource_type == "Observation":
                value = resource.get("valueString", "")
                if value:
                    clinical_text.append(value)
                code = resource.get("code", {})
                if code.get("text"):
                    clinical_text.append(code["text"])

        return {
            "success": True,
            "clinical_note": " ".join(filter(None, clinical_text)),
            "patient_info": patient_info,
            "source": "fhir"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "clinical_note": "",
            "patient_info": {},
            "source": "fhir"
        }


def parse_hl7_message(hl7_text: str) -> dict:
    """
    Parse a basic HL7 v2 message and extract clinical text.
    """
    try:
        segments = hl7_text.strip().split('\n')
        clinical_text = []
        patient_info = {}

        for segment in segments:
            fields = segment.split('|')
            segment_type = fields[0] if fields else ""

            if segment_type == "PID":
                if len(fields) > 5:
                    name_parts = fields[5].split('^')
                    patient_info["name"] = f"{name_parts[1] if len(name_parts) > 1 else ''} {name_parts[0]}".strip()
                if len(fields) > 7:
                    patient_info["dob"] = fields[7]

            elif segment_type == "DG1":
                if len(fields) > 3:
                    # DG1-3 format: code^description^system
                    dg1_parts = fields[3].split('^')
                    if len(dg1_parts) > 1:
                        clinical_text.append(dg1_parts[1])
                    else:
                        clinical_text.append(fields[3])

            elif segment_type == "OBX":
                if len(fields) > 5:
                    clinical_text.append(fields[5])

            elif segment_type == "NTE":
                if len(fields) > 3:
                    clinical_text.append(fields[3])

        return {
            "success": True,
            "clinical_note": " ".join(filter(None, clinical_text)),
            "patient_info": patient_info,
            "source": "hl7"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "clinical_note": "",
            "patient_info": {},
            "source": "hl7"
        }


def create_sample_fhir_bundle() -> dict:
    """Returns a sample FHIR Bundle for testing."""
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "name": [{"family": "Johnson", "given": ["Mary"]}],
                    "birthDate": "1948-06-22"
                }
            },
            {
                "resource": {
                    "resourceType": "Condition",
                    "code": {
                        "text": "Community acquired pneumonia with COPD and congestive heart failure"
                    }
                }
            }
        ]
    }


def create_sample_hl7() -> str:
    """Returns a sample HL7 v2 message for testing."""
    return """MSH|^~\\&|HIS|HOSPITAL|APP|DEST|20240101120000||ADT^A01|MSG001|P|2.5
PID|1||123456^^^MRN||Johnson^Mary^||19480622|F
DG1|1||J189^Pneumonia unspecified^ICD10|Community acquired pneumonia
DG1|2||J449^COPD unspecified^ICD10|Chronic obstructive pulmonary disease
NTE|1||Patient presents with shortness of breath and productive cough"""
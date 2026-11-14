with open('upload/core/reference_service.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = """            if is_ret:
                has_retracted = True
                retracted_citations.append({
                    "text": line,
                    "doi": doi,
                    "notice": metadata.get("retraction_notice") or status_warning
                })
                warnings.append(f"⛔ RETRACTED: Citation with DOI {doi} has been retracted ({metadata.get('title')}).")

            if is_eoc:
                has_expression_of_concern = True
                expression_of_concern_citations.append({
                    "text": line,
                    "doi": doi,
                    "warning": status_warning
                })
                warnings.append(f"⚠️ EXPRESSION OF CONCERN: Citation with DOI {doi} is under investigation.")

            if is_prep:
                has_preprint = True
                preprint_citations.append({"text": line, "doi": doi})

            if is_corr:
                has_corrected = True"""

replacement = """            if is_ret:
                status_type = "retracted"
                has_retracted = True
                retracted_citations.append({
                    "text": line,
                    "doi": doi,
                    "notice": metadata.get("retraction_notice") or status_warning or "Retracted publication."
                })
                warnings.append(f"⛔ RETRACTED: Citation with DOI {doi} has been retracted ({metadata.get('title')}).")
            elif is_eoc:
                status_type = "expression_of_concern"
                has_expression_of_concern = True
                expression_of_concern_citations.append({
                    "text": line,
                    "doi": doi,
                    "warning": status_warning or "Expression of concern."
                })
                warnings.append(f"⚠️ EXPRESSION OF CONCERN: Citation with DOI {doi} is under investigation.")
            elif is_prep:
                status_type = "preprint"
                has_preprint = True
                preprint_citations.append({"text": line, "doi": doi})
            elif is_corr:
                status_type = "corrected"
                has_corrected = True"""

assert target in text, "target not found"
text = text.replace(target, replacement, 1)

with open('upload/core/reference_service.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Updated status_type logic in reference_service.py")

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тест парсинга на сохранённых HTML файлах (без браузера).
Проверяет корректность селекторов и извлечения данных.
"""
from pathlib import Path
from bs4 import BeautifulSoup

DOCS_DIR = Path(__file__).parent / "docs"


def test_parse_search_results():
    """Парсинг таблицы результатов из Permit Status HTML"""
    html_path = DOCS_DIR / "Permit Status - MyBuildingPermit.html"
    if not html_path.exists():
        print(f"File not found: {html_path}")
        return []
    
    with open(html_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "lxml")
    
    results = []
    rows = soup.select("#searchResultsGrid tr.k-master-row")
    for row in rows[:4]:  # первые 4 для теста
        cells = row.select("td[role='gridcell']")
        if len(cells) >= 6:
            # cells[0] = Permit # (ссылка), cells[1] = Description, cells[2] = Address, ...
            permit_a = cells[0].select_one("a")
            permit_num = permit_a.get_text(strip=True) if permit_a else ""
            permit_href = permit_a.get("href", "") if permit_a else ""
            
            desc_html = cells[1].decode_contents() if hasattr(cells[1], "decode_contents") else str(cells[1])
            desc_parts = desc_html.replace("<br>", "\n").replace("<br/>", "\n").split("\n")
            project_name = desc_parts[0].strip() if desc_parts else ""
            description = desc_parts[1].strip() if len(desc_parts) > 1 else ""
            
            address = cells[2].get_text(strip=True)
            permit_type = cells[3].get_text(strip=True)
            status = cells[4].get_text(strip=True)
            applied_date = cells[5].get_text(strip=True)
            
            results.append({
                "permit_number": permit_num,
                "project_name": project_name,
                "description": description[:80] + "..." if len(description) > 80 else description,
                "address": address,
                "permit_type": permit_type,
                "status": status,
                "applied_date": applied_date,
                "url": permit_href,
            })
    
    return results


def test_parse_permit_details():
    """Парсинг страницы деталей из Permit Details HTML"""
    html_path = DOCS_DIR / "Permit Details - MyBuildingPermit.html"
    if not html_path.exists():
        print(f"File not found: {html_path}")
        return None
    
    with open(html_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "lxml")
    
    def get_val(label):
        th = soup.find("th", string=lambda t: t and label in t)
        if th:
            td = th.find_next_sibling("td")
            if td:
                return td.get_text(strip=True)
        return None
    
    # People grid - строки в tbody
    people = []
    people_table = soup.select_one("#permitPeopleGrid table tbody")
    if people_table:
        for tr in people_table.select("tr"):
            tds = tr.select("td")
            if len(tds) >= 3:
                people.append({
                    "type": tds[0].get_text(strip=True),
                    "name": tds[1].get_text(strip=True),
                    "license": tds[2].get_text(strip=True),
                })
    
    contractor = next((p["name"] for p in people if p["type"] == "Contractor"), "")
    applicant = next((p["name"] for p in people if p["type"] == "Applicant"), "")
    
    return {
        "project_name": get_val("Project Name:"),
        "jurisdiction": get_val("Jurisdiction:"),
        "permit_type": get_val("Type:"),
        "address": get_val("Address:"),
        "parcel": get_val("Parcel:"),
        "status": get_val("Status:"),
        "applied_date": get_val("Applied Date:"),
        "issued_date": get_val("Issued Date:"),
        "applicant": applicant,
        "contractor": contractor,
        "is_owner_builder": not contractor or contractor.strip() == "",
    }


if __name__ == "__main__":
    print("=" * 60)
    print("Test 1: Parse Search Results (from saved HTML)")
    print("=" * 60)
    search_results = test_parse_search_results()
    for i, r in enumerate(search_results, 1):
        print(f"\n{i}. {r['permit_number']} | {r['address']}")
        print(f"   Type: {r['permit_type']} | Status: {r['status']} | Applied: {r['applied_date']}")
    
    print("\n" + "=" * 60)
    print("Test 2: Parse Permit Details (from saved HTML)")
    print("=" * 60)
    details = test_parse_permit_details()
    if details:
        print(f"Project: {details['project_name']}")
        print(f"Address: {details['address']} | Parcel: {details['parcel']}")
        print(f"Type: {details['permit_type']} | Status: {details['status']}")
        print(f"Applicant: {details['applicant']}")
        print(f"Contractor: {details['contractor']}")
        print(f"Owner-Builder: {details['is_owner_builder']}")

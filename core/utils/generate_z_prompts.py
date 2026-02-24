import os

def generate_prompts():
    certs = {
        "CFA (Chartered Financial Analyst)": [
            "Level 1: Ethical & Professional Standards, Quant, Economics, FSA, Corporate Issuers.",
            "Level 2: Equity, Fixed Income, Derivatives, Alternative Investments.",
            "Level 3: Portfolio Management and Wealth Planning."
        ],
        "ACCA (Association of Chartered Certified Accountants)": [
            "Applied Knowledge: BT, MA, FA.",
            "Applied Skills: LW, PM, TX, FR, AA, FM.",
            "Strategic Professional: SBL, SBR, and Options (AFM, APM, ATX, AAA)."
        ],
        "ICAEW (ACA)": [
            "Certificate Level: Accounting, Assurance, Business Tech, Law, Management Info, Principle of Tax.",
            "Professional Level: FAR, AA, TC, BST, BPB, BPT.",
            "Advanced Level: CR, SBM, Case Study."
        ],
        "CIMA (CGMA)": [
            "Operational Level: E1, P1, F1.",
            "Management Level: E2, P2, F2.",
            "Strategic Level: E3, P3, F3."
        ],
        "CPA Australia": [
            "Compulsory: Ethics & Governance, Strategic Management Accounting, Financial Reporting, Global Strategy & Leadership.",
            "Electives: Australia Taxation, Advanced Audit, Contemporary Business Issues, etc."
        ],
        "CIA (Certified Internal Auditor - IIA)": [
            "Part 1: Essentials of Internal Auditing.",
            "Part 2: Practice of Internal Auditing.",
            "Part 3: Business Knowledge for Internal Auditing."
        ],
        "CMA (Certified Management Accountant - IMA US)": [
            "Part 1: Financial Planning, Performance, and Analytics.",
            "Part 2: Strategic Financial Management."
        ],
        "FRM (Financial Risk Manager - GARP)": [
            "Part I: Foundations of Risk Management, Quantitative Analysis, Financial Markets and Products, Valuation and Risk Models.",
            "Part II: Market Risk Measurement and Management, Credit Risk Measurement and Management, Operational Risk and Resiliency, Liquidity and Treasury Risk Measurement and Management, Risk Management and Investment Management, Current Issues in Financial Markets."
        ],
        "CISA (Certified Information Systems Auditor - ISACA)": [
            "Domain 1: Information System Auditing Process.",
            "Domain 2: Governance and Management of IT.",
            "Domain 3: Information Systems Acquisition, Development, and Implementation.",
            "Domain 4: Information Systems Operations and Business Resilience.",
            "Domain 5: Protection of Information Assets."
        ],
        "IFRS Certificate/Diploma (ACCA/ICAEW)": [
            "International Financial Reporting Standards (IFRS) core concepts.",
            "Presentation of Financial Statements, Asset and Liability accounting, Group accounting, and Disclosure requirements."
        ]
    }

    prompt_template = """Hello GLM-5 (Z.ai), as a professional international education researcher, please conduct an in-depth analysis of the **Pain Point Topics** (the most challenging topics for learners) of the **{cert_name}** certification.

Please cover the ENTIRE syllabus, including:
{syllabus}

Specific Requirements:
1. Identify **as many specific topics/chapters as possible** across the entire syllabus that have high failure rates, are historically difficult, or cause the most confusion (e.g., Absorption Costing, Deferred Tax, Options Greeks, Consolidation, Audit Risk Assessment, etc.). Aim for an exhaustive list.
2. For EACH identified topic, explain **WHY** it is difficult for learners (the 'pain points').
3. Propose creative **Gamification** mechanics to help learners master these topics (e.g., simulations, card-battles, detective-style investigations, etc.).
4. Provide the entire response in **English**, ensuring high-quality, actionable insights for professional education development.

Please format your report clearly with headings and bullet points."""

    output_content = "# PARALLEL RESEARCH PROMPT BUNDLE (Z.AI - ENGLISH)\n\n"
    output_content += "> [!IMPORTANT]\n"
    output_content += "> Copy each section below into 5 different chat tabs on [chat.z.ai](https://chat.z.ai) to run queries in parallel.\n\n"

    for i, (name, syllabus_list) in enumerate(certs.items(), 1):
        syllabus_str = "\n".join([f"- {s}" for s in syllabus_list])
        prompt = prompt_template.format(cert_name=name, syllabus=syllabus_str)
        output_content += f"## {i}. PROMPT FOR {name.split('(')[0].strip()}\n"
        output_content += "```text\n"
        output_content += prompt + "\n"
        output_content += "```\n\n"

    with open("z_ai_prompts.md", "w", encoding="utf-8") as f:
        f.write(output_content)
    
    print("Prompts generated in z_ai_prompts.md")

if __name__ == "__main__":
    generate_prompts()

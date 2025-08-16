from datetime import date

def make_prompt(title, company, location, description, job_details_retrieved, applicant_details_retrieved):
    evidence = "\n\n".join([f"[Snippet {i+1}] {t}" for i,(t,_) in enumerate(job_details_retrieved)])
    applicant_snippets = "\n\n".join([f"[Applicant Snippets {i+1}] {t}" for i,(t,_) in enumerate(applicant_details_retrieved)])
    system = f"""
You write tailored cover letters. Use ONLY the provided snippets as factual evidence.
Do not invent employers, dates, titles, or skills not present in snippets. 
Do not reference snippets, but use the content directly.    
"""
    prompt = f"""
Job title: 
{title}

Job company:
{company}

Job location:
{location}

Job description:
{description}

Evidence snippets:
{evidence}

Applicant details snippets:
{applicant_snippets}

Date of application: 
{date.today().isoformat()}

Write a one-page cover letter:
- Professional letterhead with sender's name, contact details, and location, the date and the inside address, name, attention line and location
- 2 short paragraphs + 3 bullet points
- Reference the company's needs explicitly
- Only include facts supported by snippets (cite them)
- Finish with a friendly call to action with the applicant's name
"""
    return system, prompt
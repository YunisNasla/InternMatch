"""Write the six made-up test resumes (5 PDFs, 1 DOCX). Every person here is fictional.

Run from backend/: .venv/bin/python -m tests.fixtures.make_resumes
"""

from pathlib import Path

import docx

OUT = Path(__file__).parent / "resumes"

RESUMES = {
    "cs_maya_chen.pdf": """Maya Chen | San Jose, CA | maya.chen@example.com
San Jose State University, B.S. Computer Science, Expected May 2028, GPA 3.7
Skills: Python, TypeScript, Go, SQL, React, Node.js, Docker, AWS Lambda, PostgreSQL, Git
Experience
Software Engineering Intern, Harborline Payments (Jun 2025 - Aug 2025)
- Built a fraud-alert microservice in Go that handled 2,000 requests per second
- Cut CI build time from 14 to 6 minutes by caching Docker layers
Teaching Assistant, SJSU Data Structures (Jan 2026 - present)
- Run weekly labs for 45 students on trees, graphs and hashing
Projects
Campus Eats: React + Node app for ordering from campus food trucks, 600 monthly users
Tiny Raft: a Raft consensus implementation in Go with leader election and log replication
Coursework: Operating Systems, Distributed Systems, Algorithms, Databases, Machine Learning""",
    "me_diego_ramirez.pdf": """DIEGO RAMIREZ - Pomona, CA - diego.r@example.com
Cal Poly Pomona, Mechanical Engineering. Graduating Spring 2028. GPA 3.4
TOOLS: SolidWorks, Ansys Fluent, MATLAB, Python, GD&T, CNC mill, TIG welding, 3D printing
EXPERIENCE
Formula SAE, Powertrain Lead, Fall 2024 - present
- Designed an intake manifold in SolidWorks and validated airflow with Ansys Fluent CFD
- Machined throttle body parts on a CNC mill, cutting part cost by 30 percent
Manufacturing Intern, Pacific Valve Co (Summer 2025)
- Wrote work instructions for 12 assembly stations and reduced rework by 15 percent
PROJECTS
Thermoelectric cooler test stand: Arduino data logging, PID temperature control
Coursework: Thermodynamics, Heat Transfer, Machine Design, Fluid Mechanics, Controls""",
    "ee_priya_nair.pdf": """Priya Nair
1200 Guadalupe St, Apt 4B, Austin, TX 78701 | priya.nair@example.com
The University of Texas at Austin, B.S. Electrical and Computer Engineering, Expected 12/2027, GPA 3.8
Technical skills: C, C++, Verilog, Python, MATLAB, Altium Designer, oscilloscope, logic analyzer, soldering
Experience
Embedded Systems Intern, Lonestar Avionics (May 2025 - Aug 2025)
- Wrote STM32 firmware in C for a flight sensor board, sampling an IMU at 1 kHz
- Brought up a new 4-layer PCB and fixed two power rail faults with the oscilloscope
Undergraduate Researcher, UT Power Electronics Lab (Sep 2025 - present)
- Simulate GaN buck converters in LTspice and measure efficiency on the bench
Projects
FPGA audio equalizer in Verilog on a Basys 3 board
Coursework: Digital Logic, Embedded Systems, Signals and Systems, Power Electronics, Electromagnetics""",
    "bio_jordan_ellis.pdf": """Jordan Ellis | Boston, Massachusetts | jordan.ellis@example.com
Northeastern University, B.S. Biology (Concentration: Cell and Molecular), Expected May 2027, GPA 3.6
LAB SKILLS: PCR, qPCR, Western blot, ELISA, mammalian cell culture, flow cytometry, aseptic technique
COMPUTER: R, Python (pandas), GraphPad Prism, ImageJ, Benchling
EXPERIENCE
Research Co-op, Bayview Therapeutics (Jan 2026 - Jun 2026)
- Ran ELISA and Western blot assays on about 200 samples for an antibody screening program
- Kept cell lines for 3 projects and wrote 4 SOPs for the team
Undergraduate Research Assistant, Northeastern Immunology Lab (Sep 2024 - Dec 2025)
- Stained T cells and ran flow cytometry to measure activation markers
PROJECTS
Senior capstone: CRISPR knockout of a stress-response gene in yeast, measured by qPCR
Coursework: Molecular Biology, Immunology, Biochemistry, Genetics, Biostatistics""",
    "nonstem_taylor_brooks.pdf": """Taylor Brooks | Chicago, IL | taylor.brooks@example.com
DePaul University, B.A. Marketing, minor in Communications, Expected June 2027, GPA 3.5
Skills: Social media strategy, Canva, Hootsuite, copywriting, Google Analytics, event planning, Excel
Experience
Marketing Intern, Lakeshore Coffee Roasters (Jun 2025 - Sep 2025)
- Planned and posted 60 Instagram posts, growing followers by 25 percent
- Helped run two pop-up tasting events with 300 guests each
Campus Ambassador, StudyBuddy App (Sep 2025 - present)
- Recruited 150 student users through tabling and class talks
Projects
Brand refresh plan for a local bookstore: survey of 80 customers and a new social media calendar
Coursework: Consumer Behavior, Brand Management, Public Relations, Business Writing""",
}

DOCX_RESUME = ("chem_sam_okafor.docx", [
    "Sam Okafor",
    "Ann Arbor, MI | sam.okafor@example.com",
    "University of Michigan, B.S. Chemistry, Graduating Winter 2027, GPA 3.5",
    "LAB SKILLS: HPLC, GC-MS, NMR, UV-Vis spectroscopy, titration, organic synthesis, glovebox",
    "SOFTWARE: ChemDraw, MestReNova, Python, Excel",
    "EXPERIENCE",
    "Undergraduate Researcher, Michigan Catalysis Group (Jan 2025 - present)",
    "- Synthesize palladium catalysts and track yields by GC-MS across 40 reactions",
    "- Wrote a Python script that turns raw HPLC exports into yield tables",
    "Quality Control Intern, Great Lakes Coatings (Summer 2025)",
    "- Ran titrations and viscosity tests on 30 batches a week",
    "Coursework: Organic Chemistry I and II, Physical Chemistry, Analytical Chemistry, Inorganic Chemistry",
])


def make_pdf(text: str) -> bytes:
    """A one-page, text-based PDF in Helvetica, enough for pdfplumber to read."""
    lines = [ln.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") for ln in text.splitlines()]
    stream = "BT /F1 9 Tf 40 760 Td 13 TL " + " ".join(f"({ln}) Tj T*" for ln in lines) + " ET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> "
            "/Contents 5 0 R >>"
        ),
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
    ]
    out, offsets = "%PDF-1.4\n", []
    for i, body in enumerate(objects, 1):
        offsets.append(len(out.encode("latin-1")))
        out += f"{i} 0 obj\n{body}\nendobj\n"
    xref = len(out.encode("latin-1"))
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n" + "".join(f"{o:010d} 00000 n \n" for o in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    return out.encode("latin-1")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for name, text in RESUMES.items():
        (OUT / name).write_bytes(make_pdf(text))
    name, paragraphs = DOCX_RESUME
    document = docx.Document()
    for p in paragraphs:
        document.add_paragraph(p)
    document.save(OUT / name)
    print(f"wrote {len(RESUMES) + 1} resumes to {OUT}")


if __name__ == "__main__":
    main()

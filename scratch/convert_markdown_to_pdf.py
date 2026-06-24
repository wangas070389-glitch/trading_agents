import os
import sys
from fpdf import FPDF

class StrategyPDF(FPDF):
    def header(self):
        # Header on every page (except the title page)
        if self.page_no() > 1:
            self.set_font("helvetica", "I", 8)
            self.set_text_color(128, 128, 128)
            self.cell(self.epw / 2, 10, "Strategy Specification & Scenario Walkthrough Deep Dive", border=0, align="L")
            self.cell(self.epw / 2, 10, f"Page {self.page_no()}", border=0, align="R")
            self.ln(10)
            self.line(15, 20, 195, 20)
            self.ln(5)

    def footer(self):
        # Footer on every page (except the title page)
        if self.page_no() > 1:
            self.set_y(-15)
            self.set_font("helvetica", "I", 8)
            self.set_text_color(128, 128, 128)
            self.cell(self.epw, 10, "Confidential - Trading System Documentation", border=0, align="C")

def convert_md_to_pdf(md_path, pdf_path):
    pdf = StrategyPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(15, 20, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # ------------------ TITLE PAGE ------------------
    pdf.add_page()
    pdf.set_y(50)
    pdf.set_font("helvetica", "B", 24)
    pdf.set_text_color(24, 43, 73) # Deep Blue
    pdf.multi_cell(pdf.epw, 12, "Quantitative Trading Strategies", align="C")
    pdf.multi_cell(pdf.epw, 12, "Deep Dive Specification", align="C")
    
    pdf.ln(10)
    pdf.set_font("helvetica", "I", 12)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(pdf.epw, 10, "Systematic DCF Value-Growth & MACD Trailing-Stop Strategies", align="C", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_y(180)
    pdf.set_font("helvetica", "B", 11)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(pdf.epw, 6, "Author: Antigravity Trading Systems", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 10)
    pdf.cell(pdf.epw, 6, "Status: Verified & Live Scheduled", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(pdf.epw, 6, "Platform: Alpaca Paper Trading / BMV Mock Engine", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(pdf.epw, 6, "Date: June 2026", align="C", new_x="LMARGIN", new_y="NEXT")
    
    # ------------------ CONTENT PAGES ------------------
    pdf.add_page()
    pdf.set_text_color(0, 0, 0)
    
    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    in_code_block = False
    in_math_block = False
    code_content = []
    math_content = []
    
    i = 0
    while i < len(lines):
        line = lines[i].rstrip("\n")
        
        # Handle code blocks
        if line.strip().startswith("```"):
            if in_code_block:
                # End of code block, draw it
                pdf.set_font("courier", "", 9)
                pdf.set_fill_color(240, 240, 240)
                pdf.set_text_color(50, 50, 50)
                pdf.multi_cell(pdf.epw, 4, "\n".join(code_content), border=1, fill=True)
                pdf.ln(3)
                in_code_block = False
                code_content = []
            else:
                in_code_block = True
            i += 1
            continue
            
        if in_code_block:
            code_content.append(line)
            i += 1
            continue
            
        # Handle standalone LaTeX blocks
        if line.strip() == "$$" or (line.strip().startswith("$$") and line.strip().endswith("$$") and len(line.strip()) > 2):
            # Check if it's inline on a single line or start of block
            stripped = line.strip()
            if stripped.startswith("$$") and stripped.endswith("$$") and len(stripped) > 2:
                # Single line equation
                eq = stripped[2:-2].strip()
                pdf.set_font("courier", "I", 10)
                pdf.set_text_color(30, 80, 150)
                pdf.multi_cell(pdf.epw, 6, f"    {eq}", align="C")
                pdf.ln(3)
                pdf.set_text_color(0, 0, 0)
            else:
                # Start of block
                if in_math_block:
                    # End of block
                    pdf.set_font("courier", "I", 10)
                    pdf.set_text_color(30, 80, 150)
                    pdf.multi_cell(pdf.epw, 6, "\n".join(math_content), align="C")
                    pdf.ln(3)
                    pdf.set_text_color(0, 0, 0)
                    in_math_block = False
                    math_content = []
                else:
                    in_math_block = True
            i += 1
            continue
            
        if in_math_block:
            math_content.append(line)
            i += 1
            continue
            
        # Skip top level header since we have a title page
        if line.startswith("# ") and not line.startswith("## "):
            i += 1
            continue
            
        # Headers
        if line.startswith("## "):
            header_text = line[3:].strip()
            pdf.ln(5)
            pdf.set_font("helvetica", "B", 14)
            pdf.set_text_color(24, 43, 73) # Deep Blue
            pdf.multi_cell(pdf.epw, 8, header_text)
            pdf.ln(2)
            pdf.set_text_color(0, 0, 0)
            i += 1
            continue
            
        if line.startswith("### "):
            header_text = line[4:].strip()
            pdf.ln(3)
            pdf.set_font("helvetica", "B", 11)
            pdf.set_text_color(80, 80, 80)
            pdf.multi_cell(pdf.epw, 6, header_text)
            pdf.ln(1)
            pdf.set_text_color(0, 0, 0)
            i += 1
            continue
            
        # Lists
        if line.strip().startswith("* ") or line.strip().startswith("- "):
            clean_line = line.strip()[2:].strip()
            pdf.set_font("helvetica", "", 10)
            pdf.cell(10, 5, chr(149), align="R") # bullet character
            pdf.multi_cell(pdf.epw - 10, 5, clean_line)
            i += 1
            continue
            
        if line.strip().startswith("1. ") or line.strip().startswith("2. ") or line.strip().startswith("3. ") or line.strip().startswith("4. ") or line.strip().startswith("5. "):
            clean_line = line.strip()
            parts = clean_line.split(". ", 1)
            num = parts[0] + "."
            content = parts[1]
            pdf.set_font("helvetica", "B", 10)
            pdf.cell(10, 5, f" {num}", align="R")
            pdf.set_font("helvetica", "", 10)
            pdf.multi_cell(pdf.epw - 10, 5, content)
            i += 1
            continue
            
        # Horizontal rule
        if line.strip() == "---":
            pdf.ln(3)
            pdf.line(15, pdf.get_y(), 195, pdf.get_y())
            pdf.ln(3)
            i += 1
            continue
            
        # Empty lines
        if not line.strip():
            pdf.ln(2)
            i += 1
            continue
            
        # Handle paragraph text
        pdf.set_font("helvetica", "", 10)
        # Parse inline latex equations like $$ ... $$ inside paragraphs
        if "$$" in line:
            parts = line.split("$$")
            for idx, part in enumerate(parts):
                if idx % 2 == 1:
                    pdf.set_font("courier", "I", 10)
                    pdf.set_text_color(30, 80, 150)
                else:
                    pdf.set_font("helvetica", "", 10)
                    pdf.set_text_color(0, 0, 0)
                pdf.write(5, part)
            pdf.ln(5)
        else:
            pdf.multi_cell(pdf.epw, 5, line)
            
        i += 1
        
    pdf.output(pdf_path)
    print(f"Successfully converted MD to PDF: {pdf_path}")

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    md_path = r"C:\Users\z003puwx\Desktop\Antigravity_Projects\trade\trading_agents\scratch\strategy_deep_dive.md"
    # Wait, let's make sure we check where the markdown file is. We saved it in the artifacts folder, but we can also copy/read it from there.
    # The absolute path of the artifact was:
    md_path = r"C:\Users\z003puwx\.gemini\antigravity-ide\brain\d267b4b3-2093-4152-8e79-4f0183ac287f\strategy_deep_dive.md"
    pdf_path = r"C:\Users\z003puwx\.gemini\antigravity-ide\brain\d267b4b3-2093-4152-8e79-4f0183ac287f\strategy_deep_dive.pdf"
    
    convert_md_to_pdf(md_path, pdf_path)

if __name__ == "__main__":
    main()

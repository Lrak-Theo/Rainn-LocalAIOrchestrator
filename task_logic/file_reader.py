# ==========================================
# File: file_reader.py
# Updated in iteration: 4
# Author: Karl Concha
#
# ChatGPT (OpenAI, 2025) – Assisted in refining
# file-handling structure and ensuring consistent
# read-function routing for PDF, TXT, and CSV files.
# Conversation Topic: "Iteration 2 – File reading
# utilities for Rainn (PDF/TXT/CSV support)."
# Date of assistance: November 2025
#
# References:
# - PyPDF2 Documentation – https://pypdf2.readthedocs.io/
# - Python CSV Module – https://docs.python.org/3/library/csv.html
# ==========================================

import csv 
from PyPDF2 import PdfReader

class FileReader:

    @staticmethod
    def read_file(file_path):
        if file_path.endswith(".pdf"):
            return FileReader.read_pdf(file_path)
        elif file_path.endswith(".txt"):
            return FileReader.read_txt(file_path)
        elif file_path.endswith(".csv"):
            return FileReader.read_csv(file_path)
        else:
            return "[Unsupported file type]"

    @staticmethod
    #This is how using PyPDF2 can enable Rainn to read pdf files
    #Basically a text extractor which is added into a var (or array) combined with breaks using \n
    def read_pdf(path):
        reader = PdfReader(path)
        
        plain_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                plain_text += text + '\n'
        
        plain_text = plain_text.replace("\r\n", "\n").replace("\r", "\n")

        if "\n" not in plain_text and len(plain_text) > 250:
            plain_text = plain_text.replace(". ", ".\n")
        
        return plain_text

    # Simple helper for reading txt files from the project directory.
    @staticmethod
    def read_txt(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    #Utilising csv in order to read excel spreadsheets, in later iterations need to have a function to convert them automatically
    @staticmethod
    def read_csv(path):
        rows = []
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                rows.append(", ".join(row))
        return "\n".join(rows)

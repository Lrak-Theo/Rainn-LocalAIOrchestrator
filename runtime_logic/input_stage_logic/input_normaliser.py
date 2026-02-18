# ==========================================
# File: input_normaliser.py
# Updated in iteration: 4
# Author: Karl Concha
#
# - Read uploaded file (.txt / .pdf / .csv)
# - NORMALISE extracted content to plain text for AI model to read
# - Write initial artifact: 00_input_original.txt
# 
# #ChatGPT (OpenAI, 2025) – Assisted in structuring the Stage 0 input
# normalisation process, defining the plain-text contract, and enforcing
# artifact persistence (00_input_original.txt) for traceability.
# Conversation Topic: "Input Normalisation and Artifact outputs"
# Date: January 2026
# Used in agent_runtime_servcice.py
# ==========================================

import os
from task_logic.file_reader import FileReader


class InputNormaliser:
    """
    Stage 0 (Input) handler: read → normalise → persist as artifact.
    """

    @staticmethod
    def run_multi(files, run_folder):
        """
        Reads and normalises multiple uploaded files and writes 00_input_original.txt.
        Each file is separated with a clear header for traceability.
        """

        if not files:
            raise Exception("No files provided")
        
        array_file = []

        for item in files:
            file_name = item["name"] # Retreiving the name key in the files dict
            file_path = item["path"] # Retreiving the path key in the files dict

            text = FileReader.read_file(file_path)

            if not text:
                raise Exception(f"No Content extracted from {file_name}")
            if text == "[Unsupported file type]":
                raise Exception(f"Unsupported file type: {file_name}")

            text = "\n".join(text.splitlines()).strip() 
            # Splitting text into a list of lines while joining the lines again using \n

            array_file.append(f"{file_name}: \n{text}")

        # Write input stage artifact for traceback purposes
        text_combined = "\n\n".join(array_file)
        artifact_path = os.path.join(run_folder, "input_original.txt")
        with open(artifact_path, "w", encoding="utf-8") as f:
            f.write(text_combined)

        return text_combined, artifact_path

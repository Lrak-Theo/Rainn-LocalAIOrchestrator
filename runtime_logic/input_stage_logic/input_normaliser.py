import os
from runtime_logic.input_stage_logic.file_reader import FileReader


class InputNormaliser:
    # Why is input normaliser needed? In order to safely process all different forms of files into one format that the model can read

    @staticmethod
    def run_multi(files, artifacts_directory, stage_index=1):
        """
        Reads and normalises multiple uploaded files and writes 01_stage_input_output.txt.
        Each file is separated with a clear header for traceability.
        """

        if not files:
            raise Exception("No files provided")
        
        # Create an file list
        array_file = []


        for item in files:

            # Retreiving the name key in the files dict
            file_name = item["name"]

            # Retreiving the path key in the files dict
            file_path = item["path"] 

            # Location where FileReader is used
            text = FileReader.read_file(file_path) 

            # Error handling...
            if not text:
                raise Exception(f"No Content extracted from {file_name}")
            
            if text == "[Unsupported file type]":
                raise Exception(f"Unsupported file type: {file_name}")
            

            # Splitting text into a list of lines while joining the lines again using \n
            text = "\n".join(text.splitlines()).strip() 
           
            # Combine the file name and text into one string into then adding it into the file array list
            array_file.append(f"{file_name}: \n{text}")



        # Write input stage artifact into now a string with sections
        text_combined = "\n\n".join(array_file)

        # Assign the artifact filename into a variable 
        artifact_filename = f"{stage_index:02d}_stage_input_output.txt"

        # Then find the path
        artifact_path = os.path.join(artifacts_directory, artifact_filename)

        # Which is then written into the correct file path with the normalised string
        with open(artifact_path, "w", encoding="utf-8") as f:
            f.write(text_combined)

        # while returning the artifact path
        return artifact_path

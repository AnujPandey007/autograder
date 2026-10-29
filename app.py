import tempfile
from pathlib import Path
import gradio as gr

from grader import grade_submission
from feedback import make_feedback, save_reports


def evaluate(first_file, extra_files, instructor_file, test_file):
    if not first_file or not instructor_file or not test_file:
        return "Upload the first C file and both JSON files.", None, None

    extra_files = extra_files or []
    if len(extra_files) > 4:
        return "Upload at most 4 comparison files.", None, None

    # Grade only the first file. Other files are comparison references.
    report = grade_submission(
        first_file,
        instructor_file,
        test_file,
        peers=extra_files
    )

    folder = Path(tempfile.mkdtemp(prefix="autograder-report-"))
    json_file, text_file = save_reports([report], folder / "results.json")

    return make_feedback(report), json_file, text_file


def build_app():
    with gr.Blocks(title="C AutoGrader") as app:
        gr.Markdown(
            "# C AutoGrader\n"
            "Upload one C file to grade. Optionally add up to four "
            "C files for originality comparison only. "
            "All files should answer the same question."
        )

        first_file = gr.File(
            label="C file to grade (required)",
            file_types=[".c"],
            type="filepath"
        )

        extra_files = gr.File(
            label="Comparison C files (optional, maximum 4)",
            file_types=[".c"],
            file_count="multiple",
            type="filepath"
        )

        instructor_file = gr.File(
            label="Instructor JSON",
            file_types=[".json"],
            type="filepath"
        )

        test_file = gr.File(
            label="Test-cases JSON",
            file_types=[".json"],
            type="filepath"
        )

        button = gr.Button("Generate report")
        result = gr.Textbox(label="Grading report", lines=20)
        json_report = gr.File(label="Download JSON report")
        text_report = gr.File(label="Download text report")

        button.click(
            fn=evaluate,
            inputs=[first_file, extra_files, instructor_file, test_file],
            outputs=[result, json_report, text_report],
            concurrency_limit=1
        )

    return app


if __name__ == "__main__":
    build_app().queue(max_size=8).launch(
        server_name="127.0.0.1",
        share=False,
        max_file_size="1mb"
    )
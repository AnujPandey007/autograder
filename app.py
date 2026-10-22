import gradio as gr

def upload_file(file):
    if file is None:
        return "Please upload a file."
    return "File uploaded: " + file

app = gr.Interface(
    fn=upload_file,
    inputs=gr.File(label="Upload C file"),
    outputs="text"
)

app.launch()

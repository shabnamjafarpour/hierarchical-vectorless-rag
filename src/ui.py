import gradio as gr

from src.pipeline import process_document
from src.generation.answer_generator import (
    answer_question,
)


def create_ui(
    llm,
    model_name: str,
):
    """
    Create the Gradio interface for document
    processing and question answering.
    """

    # Holds the currently processed document
    document_state = gr.State(None)

    # -----------------------------------------
    # Process uploaded PDF
    # -----------------------------------------

    def process_uploaded_document(file_path):

        if not file_path:
            return (
                None,
                "❌ Please upload a PDF first.",
            )

        try:
            processed_document = process_document(
                file_path=file_path,
                llm=llm,
                model_name=model_name,
            )

            metadata = processed_document[
                "metadata"
            ]

            status = (
                "✅ Document ready\n\n"
                f"File: {metadata.get('filename', '')}\n\n"
                f"Pages: {metadata.get('num_pages', '')}"
            )

            return (
                processed_document,
                status,
            )

        except Exception as error:

            print(
                ">>> Document processing error:",
                error,
            )

            return (
                None,
                f"❌ Processing failed: {error}",
            )

    # -----------------------------------------
    # Chat
    # -----------------------------------------

    def chat(
        message,
        history,
        processed_document,
    ):

        if processed_document is None:
            return (
                "Please upload and process "
                "a document first."
            )

        if not message.strip():
            return ""

        document_tree = processed_document[
            "tree"
        ]

        try:
            result = answer_question(
                query=message,
                document_tree=document_tree,
                llm=llm,
            )

            return result["answer"]

        except Exception as error:

            print(
                ">>> Question answering error:",
                error,
            )

            return (
                f"An error occurred while "
                f"answering the question: {error}"
            )

    # -----------------------------------------
    # UI
    # -----------------------------------------

    with gr.Blocks(
        title="Hierarchical Vectorless RAG"
    ) as demo:

        gr.Markdown(
            """
# Hierarchical Vectorless RAG

Upload a PDF, process the document, and ask
questions about its content.
"""
        )

        with gr.Row():

            pdf_input = gr.File(
                label="Upload PDF",
                file_types=[".pdf"],
                type="filepath",
            )

            process_button = gr.Button(
                "Process Document",
                variant="primary",
            )

        status_output = gr.Markdown(
            "No document loaded."
        )

        chatbot = gr.Chatbot(
            height=450,
        )

        chat_interface = gr.ChatInterface(
            fn=chat,
            chatbot=chatbot,
            additional_inputs=[
                document_state,
            ],
            textbox=gr.Textbox(
                placeholder=(
                    "Ask a question about "
                    "the document..."
                ),
                label="Question",
            ),
        )

        process_button.click(
            fn=process_uploaded_document,
            inputs=[
                pdf_input,
            ],
            outputs=[
                document_state,
                status_output,
            ],
        )

    return demo
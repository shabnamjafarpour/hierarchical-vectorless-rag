import gradio as gr

from src.pipeline import process_document
from src.generation.answer_generator import answer_question


CUSTOM_CSS = """
/* =========================================================
   Application layout
   ========================================================= */

.gradio-container {
    max-width: 1180px !important;
    margin: 0 auto !important;
}

/* =========================================================
   Header
   ========================================================= */

#app-header {
    text-align: center;
    margin-top: 20px;
    margin-bottom: 28px;
}

/* =========================================================
   Fixed chatbot height
   ========================================================= */

#chatbot {
    height: 520px !important;
    min-height: 520px !important;
    max-height: 520px !important;
    overflow: hidden !important;
}

/* Keep the message area scrollable instead of expanding */
#chatbot .wrap,
#chatbot .bubble-wrap {
    max-height: 520px !important;
    overflow-y: auto !important;
}


#app-header h1 {
    font-size: 34px !important;
    font-weight: 700 !important;
    margin-bottom: 8px !important;
}

#chatbot {
    height: 480px !important;
    min-height: 480px !important;
    max-height: 480px !important;
    overflow: hidden !important;
}

#chatbot .wrap,
#chatbot .bubble-wrap {
    max-height: 480px !important;
    overflow-y: auto !important;
}

#app-header p {
    font-size: 16px !important;
    opacity: 0.75;
    margin: 0 !important;
}

/* =========================================================
   Upload section
   ========================================================= */

#upload-section {
    max-width: 680px;
    margin: 0 auto 12px auto !important;
}

#pdf-upload {
    min-height: 150px;
}

#process-button {
    max-width: 220px !important;
    margin: 14px auto 0 auto !important;
}

/* =========================================================
   Document status
   ========================================================= */

#document-status {
    max-width: 680px;
    margin: 12px auto 28px auto !important;
    text-align: center;
    font-size: 15px;
}

#document-status p {
    margin: 0 !important;
}

/* =========================================================
   Chat container
   ========================================================= */

#chat-section {
    margin-top: 8px;
}

#chatbot {
    border-radius: 12px;
}

/* Slightly larger chat typography */
#chatbot .message {
    font-size: 17px !important;
    line-height: 1.9 !important;
}

/* =========================================================
   Persian / RTL chat content
   ========================================================= */

#chatbot .message p,
#chatbot .message li,
#chatbot .message ul,
#chatbot .message ol {
    direction: rtl !important;
    text-align: right !important;
}

/* Keep lists visually aligned in RTL responses */
#chatbot .message ul,
#chatbot .message ol {
    padding-right: 24px !important;
    padding-left: 0 !important;
}

/* =========================================================
   Code remains LTR
   ========================================================= */

#chatbot pre,
#chatbot code {
    direction: ltr !important;
    text-align: left !important;
}

/* =========================================================
   Question textbox
   ========================================================= */

#question-box textarea {
    font-size: 16px !important;
    line-height: 1.7 !important;
}

/* =========================================================
   Responsive layout
   ========================================================= */

@media (max-width: 768px) {
    .gradio-container {
        padding-left: 14px !important;
        padding-right: 14px !important;
    }

    #app-header h1 {
        font-size: 28px !important;
    }

    #upload-section {
        max-width: 100%;
    }

    #document-status {
        max-width: 100%;
    }
}
"""


def create_ui(
    llm,
    model_name: str,
):
    """
    Create the Gradio interface for document processing
    and grounded question answering.
    """

    document_state = gr.State(None)

    def process_uploaded_document(file_path):
        """Process an uploaded PDF and prepare it for question answering."""

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

            metadata = processed_document["metadata"]

            filename = metadata.get(
                "filename",
                "Unknown file",
            )

            num_pages = metadata.get(
                "num_pages",
                "Unknown",
            )

            status = (
                f"### ✓ Document ready\n"
                f"**{filename}** · {num_pages} pages"
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

    def chat(
        message,
        history,
        processed_document,
    ):
        """Answer a question using the currently processed document."""

        if processed_document is None:
            return (
                "Please upload and process "
                "a document first."
            )

        if not message.strip():
            return ""

        document_tree = processed_document["tree"]

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
                "An error occurred while answering "
                f"the question: {error}"
            )

    with gr.Blocks(
        title="Hierarchical Vectorless RAG",
        css=CUSTOM_CSS,
    ) as demo:

        # -------------------------------------------------
        # Header
        # -------------------------------------------------

        gr.Markdown(
            """
# Hierarchical Vectorless RAG

Hierarchical document retrieval without embeddings or a vector database.
""",
            elem_id="app-header",
        )

        # -------------------------------------------------
        # Document upload
        # -------------------------------------------------

        with gr.Column(
            elem_id="upload-section",
        ):
            pdf_input = gr.File(
                label="Upload PDF",
                file_types=[".pdf"],
                type="filepath",
                elem_id="pdf-upload",
            )

            process_button = gr.Button(
                "Process Document",
                variant="primary",
                elem_id="process-button",
            )

        status_output = gr.Markdown(
            "Upload a PDF to get started.",
            elem_id="document-status",
        )

        # -------------------------------------------------
        # Chat
        # -------------------------------------------------

        with gr.Column(
            elem_id="chat-section",
        ):
            chatbot = gr.Chatbot(
                height=480,
                elem_id="chatbot",
            )

            gr.ChatInterface(
                fn=chat,
                chatbot=chatbot,
                additional_inputs=[
                    document_state,
                ],
                textbox=gr.Textbox(
                    placeholder="Ask a question about the document...",
                    label="Question",
                    elem_id="question-box",
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
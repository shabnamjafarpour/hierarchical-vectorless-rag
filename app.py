from src.config import (
    load_model,
    MODEL_NAME,
)

from src.ui import create_ui


def main():

    llm = load_model()

    demo = create_ui(
        llm=llm,
        model_name=MODEL_NAME,
    )

    demo.launch()


if __name__ == "__main__":
    main()
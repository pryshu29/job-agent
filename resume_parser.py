import logging
import os

import fitz


logger = logging.getLogger("AI_JOB_AGENT")


MAX_RESUME_SIZE_BYTES = 10 * 1024 * 1024


def validate_pdf(file_path: str) -> None:
    logger.info(
        "RESUME | Validating PDF | file=%s",
        os.path.basename(file_path),
    )

    if not os.path.exists(file_path):
        raise FileNotFoundError(
            "Resume PDF was not found."
        )

    file_size = os.path.getsize(file_path)

    logger.info(
        "RESUME | PDF size checked | size_bytes=%s",
        file_size,
    )

    if file_size == 0:
        raise ValueError(
            "Resume PDF is empty."
        )

    if file_size > MAX_RESUME_SIZE_BYTES:
        raise ValueError(
            "Resume PDF is too large. "
            "Maximum allowed size is 10 MB."
        )


def extract_resume_text(file_path: str) -> str:

    logger.info(
        "RESUME | Starting PDF text extraction"
    )

    validate_pdf(file_path)

    document = None

    try:

        document = fitz.open(file_path)

        page_count = len(document)

        logger.info(
            "RESUME | PDF opened | pages=%s",
            page_count,
        )

        if page_count == 0:
            raise ValueError(
                "Resume PDF contains no pages."
            )

        text_parts = []

        for page_number, page in enumerate(
            document,
            start=1,
        ):

            page_text = page.get_text(
                "text"
            )

            if page_text:
                text_parts.append(
                    page_text
                )

            logger.info(
                "RESUME | Page extracted | page=%s",
                page_number,
            )

        extracted_text = "\n\n".join(
            text_parts
        ).strip()

        if not extracted_text:

            logger.warning(
                "RESUME | No text extracted from PDF"
            )

            raise ValueError(
                "No readable text was found in the PDF. "
                "The resume may be image-based or scanned."
            )

        logger.info(
            "RESUME | Text extraction successful | "
            "characters=%s",
            len(extracted_text),
        )

        return extracted_text

    except ValueError:
        raise

    except Exception:

        logger.exception(
            "RESUME | PDF extraction failed"
        )

        raise RuntimeError(
            "Unable to read the resume PDF."
        )

    finally:

        if document is not None:

            document.close()

            logger.info(
                "RESUME | PDF closed"
            )

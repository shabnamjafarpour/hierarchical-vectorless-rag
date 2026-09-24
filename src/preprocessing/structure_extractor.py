import json

from src.preprocessing.document_loader import combine_pages
from src.utils.json_utils import parse_llm_json


#در اين تابع از مدل ميخواهيم ، به ازاي داكيومنتي كه به او پاس ميدهيم
#به عنوان آرگومنت ورودي اين چهار تا عنصر رو برامون extract‌كنه
# 1. document_type
# 2. semantic_unit
# 3. fields
# 4. hierarchy
#و خروجي يك list‌خواهد بود
# كه هر عنصر آن يك partial structure خواهد بود



def discover_document_structure_batch(
    documents,
    llm,
    batch_size: int = 5,
) -> list[dict]:

    partial_structures = []
# اينجا چه اتفاقي داره ميفته ؟
#يك ليست داريم به اسم PARTIAL STRUCTURE
#به ازاي هر batch فرآيند پايين يك فايل json  معتبر 
#برميگردونه كه شامل اين چهار عنصره
# 1. document_type
# 2. semantic_unit
# 3. fields
# 4. hierarchy
    for start in range(
        0,
        len(documents),
        batch_size,
    ):
        end = min(
            start + batch_size,
            len(documents),
        )
#اينجا داره ابتدا و انتهاي بازه اي كه از صفحات داكيومنت ورميداريم رو مشخص ميكنه
#داره ميگه براي start‌از 0 شروع كن و تا انتهاي طول داكيومنت برو با گام هايي
#به طول batch size
#براي end‌ هم كه معلومه ، از start به اندازه batch برو جلو
#اما حواست باشه از طول خود داكيومنت جلوتر نري بنابراين مينيمم بگير
        print(
            f"Discovering structure between "
            f"pages {start + 1}---{end}"
        )


#اينجا هم داره تمام صفحاتي از اين داكيومنت كه داخل اين batch
# قرار داره چون قراه داخل ميخونه يك رشته واحد ميسازه
#داخل prompt تزريق بشه وبايد يك رشته باشه

        document_text = combine_pages(
            documents,
            start,
            end,
        )


# دراين پرامپت از مدل ميخواهيم بلکه از آن می‌خواهیم schema/structure را infer کند.
        prompt = f"""
You are a document structure discovery system.

Analyze the following document pages and identify
the HIGH-LEVEL semantic structure of the document.

Do NOT extract individual records yet.

Determine:

1. document_type
2. semantic_unit
3. fields
4. hierarchy

Hierarchy must contain ONLY field names
that describe relationships between records.

Example:

[
    "category",
    "author"
]

Do NOT put document titles or section names.

The semantic unit means the type of meaningful
record/entity contained in the document.

Examples include:

- product
- book
- person
- article
- event
- organization
- case
- topic
- record

Return ONLY valid JSON.

The JSON must be complete.
Do not stop before closing all brackets.

If content is large, return fewer nodes instead
of incomplete JSON.

{{
    "document_type": "",
    "semantic_unit": "",
    "fields": [],
    "hierarchy": []
}}

Rules:

- Do not extract actual records.
- Do not list individual items.
- Do not summarize the document.
- Do not invent information.
- Preserve the original language.
- Return ONLY JSON.
- Do not use Markdown.

Document pages:

{document_text}
"""

        print(">>> SENDING REQUEST TO GEMINI...")
        print(f">>> INPUT LENGTH: {len(document_text)} characters")
        response = llm.invoke(prompt)

        print(">>> GEMINI RESPONSE RECEIVED")
        print(">>> RESPONSE TYPE:", type(response.content))

        try:
            structure = parse_llm_json(response)
            partial_structures.append(structure)

        except json.JSONDecodeError as error:
            print(
                f"Could not parse structure for "
                f"pages {start + 1}-{end}."
            )
            print("Error:", error)
            print("Response:", response.content)

    return partial_structures


# Build Global Structure From Document
#هدف اين تابع اينكه ، خروجي مرحله قبل كه اومده 
#partial structure رو در آورده رو باهم تجميع كنه
#وبه يك global structure از داكيومنت اوليه ما برسه
#و خروجي دقيقا يك فايل مشخص json‌است كه  شامل اين موارد است
        # {{
        #     "document_type": "",
        #     "semantic_unit": "",
        #     "fields": [],
        #     "hierarchy": []
        # }}

# تمام partial structureها را به LLM می‌دهد و می‌گوید یک schema کلی برای document بساز.

def merge_document_structures(
    partial_structures: list[dict],
    llm,
) -> dict:


#اينجا يك ليستي از ديكشنري هارو ميگيريم
#داخل هر ليست يك فايل json‌است از structure اي كه
#از آن batch دريافت كرده است 
#و اونارو تبديل به يك متن رشته اي واحد ميكنيم
    structures_text = json.dumps(
        partial_structures,
        indent=2,
        ensure_ascii=False,
    )

    prompt = f"""
You are a document schema consolidation system.

Several partial document structure analyses
were extracted from different parts of the same document.

Your task is to merge them into ONE global schema.

Partial structures:

{structures_text}

Return ONLY valid JSON using exactly:

{{
    "document_type": "",
    "semantic_unit": "",
    "fields": [],
    "hierarchy": []
}}

Rules:

- Merge duplicate fields.
- Preserve all meaningful fields.
- Resolve minor naming differences.
- Do not invent fields.
- Do not extract actual records.
- Do not summarize the document.
- Return ONLY JSON.
- Do not use Markdown.
"""

    response = llm.invoke(prompt)

    try:
        return parse_llm_json(response)
        #اينجا داريم خروجي مدل رو تبديل ميكنيم به يك json
        #و همونو return‌ميكنيم 

    except json.JSONDecodeError as error:
        print("Could not merge document structures.")
        print("Error:", error)
        print("Response:", response.content)

        return {
            "document_type": "unknown",
            "semantic_unit": "",
            "fields": [],
            "hierarchy": [],
        }
        
# خب ممكن است سوال شود چرا از چند تا صفحه اول structure رو استخارج نكنيم؟
#جوابش اينكه بنابراین batchwise discovery باعث می‌شود بخش‌های مختلف document در 
# schema discovery مشارکت داشته باشند.
# بعد merge یک global representation می‌سازد.
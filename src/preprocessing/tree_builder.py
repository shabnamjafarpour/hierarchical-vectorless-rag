from src.utils.llm_utils import response_to_text


# چون تا الان فقط اطلاعات استخراج‌شده داشتیم؛
# این فایل آن اطلاعات را تبدیل می‌کند به ساختاری که
# بعداً Retrieval بتواند داخلش حرکت کند

#ورودي تابع ،‌semantic node هاي مرحله قبلي و 
#structure اي هست كه در مرحله قبل به دست آورديم
#در اينجا ابتدا ريشه درخت را ميگيريم و البته برايش يك فيلد
#children  مي سازيم 


def build_document_tree(
    semantic_nodes: list[dict],
    document_structure: dict,
) -> dict:

    tree = {
        "title": "Document",
        "type": "root",
        "document_type": document_structure.get(
            "document_type",
            "unknown",
        ),
        #اينجا از document structure  مي پرسه تايپ چيه
        #و اگه وجود نداشته باشه خودش unknown قرار ميده
        "semantic_unit": document_structure.get(
            "semantic_unit",
            "",
        ),
        
        #اينجا از document structure مي پرسه واحد هاي معنايي اصلي اين سند
        # چي هستند ،‌ مثلا اگه گفت Book پس tree ميدانذ كه node هاي اصلي اين درخت
        # از نوع كتاب هستند
        "summary": "",
        "children": [],
    }

    # ميره از document structure مي پرسه آيا hierarchy داري يا نه
    # كه مثلا اگه يكي از فيلد ها به عنوان مثال catagory آن فيلد بود
    #درخت را بر اساس آن بسازد كه اگر هم hierarchy نداشت پس درخت ساده مي سازد
    hierarchy = document_structure.get(
        "hierarchy",
        [],
    )

    # -----------------------------------------
    # Case 1: No hierarchy detected
    # -----------------------------------------

    if not hierarchy:

        for node in semantic_nodes:
# ميا ييم روي تمام node  ها يك loop  ميزنيم
#در واقع مياييم نود استخراج شده را به فرم tree‌تبديل ميكنيم :)
# در اينجا چون ساختار hierarchy نداريم پس همه نود ها 
#زيرمجموعه داكيومنت خواهند يود :)
            tree["children"].append(
                {
                    "title": node.get("title", ""),
                    "type": node.get(
                        "node_type",
                        "unknown",
                    ),
                    "content": node.get(
                        "content",
                        "",
                    ),
                    "metadata": node.get(
                        "metadata",
                        {},
                    ),
                    "entities": node.get(
                        "entities",
                        [],
                    ),
                    "summary": "",
                    "children": [],
                    #جون اينجا ساختار hierarchy  نداريم پس به اين معناست
                    #اين نود children‌ نداره و خالي ميمونه
                }
            )

        return tree

    # -----------------------------------------
    # Case 2: Hierarchy exists
    # -----------------------------------------


   # -----------------------------------------
    # If hierarchy exists
    #خب اين قسمت زماني اجرا ميشود كه ساختار hierarchy 
    #داشته باشيم،‌مثل زمانيكه 
    #     Document
    # │
    # ├── Science
    # │   ├── Article A
    # │   └── Article B
    # │
    # └── History
    #     ├── Article C
    #     └── Article D
    #پس مجددا همه نود هارو يكي يكي بررسي ميكنيم و جايگاه بدوي ما
    #در درخت root‌ مي باشد
    # -----------------------------------------


    for node in semantic_nodes:

        current_level = tree

        metadata = node.get(
            "metadata",
            {},
        )

#اينجا ميخواهيم روي hierarchy درخت حركت كنيم
#به عنوان مثال اگه داشته باشيم 
# hierarchy = [
#     "category",
#     "subcategory"
# ]
#آنگاه در iteration‌اول مي آييم روي category‌ و در 
#تكرار بعدي مياييم روي subcategory و به همين ترتيب در درخت ميريم پايين

        for hierarchy_level in hierarchy:


# اينجا hierarchy level ‌رو به str تبديل ميكنيم
            level_name = str( # و به عنوان مثال level value بشود science
                hierarchy_level # به عنوان مثال اين category‌باشه
            )


#در اينجا ميخواهيم مقدار آن hierarchy را در node   پيدا كنيم
#مثلا اگه داشته باشيم 
# metadata = {
#     "category": "Science"
# }
#و level_name باشه category ، عبارت پايين 
#مقدار science رو به ما برميگردونه
            level_value = metadata.get(
                level_name
            )

           
            # This semantic node does not contain
            # this hierarchy level.
        
 #حالا اگه نودي رو داريم بررسي ميكنيم كه اصلا level_value
#نداره پس بنابراين اينو رد ميكنيم و ميريم سراغ تكرار بعدي
#كه در اين مرتبه يعني category بعدي :)
            if not level_value:
                continue

            existing_child = None
#در ابتدا فرض را بر آن ميگذاريم كه child وجود نداره
#در واقع هنوز child اي پيدا نكرده ايم

            # Check whether this hierarchy node
            # already exists.
            
#در ادامه مي گوييم به ازاي children هايي كه در اين سطح 
#از درخت وجود دارند بيا حلقه پايين رو اجرا كن
            for child in current_level["children"]:

#دراينجا ميگوييم اگر type آن فرزند برابر بود با level name
# و همزمان level value   برابر بود با title آن فرزند
#يعني  داريم مپرسيم آيا فرزندي وجود داره كه هم نوعش category باشه
#و هم عنوانش sience ?  به عنوان مثال داريم
# metadata = {
#     "category": "Science"
# } 

# level_name = "category"
# level_value = "Science"

#بنابراين نتيجه ميگيريم اين همان child است و مجدد نياز نيست
#category جديد بسازيم
#مثلا اگر 50 تا مقاله داشته باشيم نميخواهيم  category مربوطه را 50 بار تكرار كنيم
# Document
# ├── Science
# ├── Science
# ├── Science
# ├── Science
# ...
# بلكه ميخواهيم 50 تا مقاله بيان برن زير مجموعه همين category‌كه وجود داره
# Document
# └── Science
#     ├── Article 1
#     ├── Article 2
#     ├── Article 3
#     └── ...


                if (
                    child.get("type") == level_name
                    and
                    child.get("title")
                    == str(level_value)
                ):
                    existing_child = child
                    break

            # Create hierarchy node if necessary.
            if existing_child is None:
#اگر هم پيدا نشد يعني اين category‌هنوز هم در درخت tree‌وجود نداره 
#پس الان وقتشه كه خودمون اون category‌رو بسازيم 

                existing_child = {
                    "title": str(level_value),
                    "type": level_name,
                    "summary": "",
                    "children": [],
                }
#واينجاست كه يك به فرزندان اين level‌اضافه مي كنيم

                current_level["children"].append(
                    existing_child
                )

            # Move one level deeper in the tree.
            current_level = existing_child
#اين خط بدين معناست حالا كه يه category‌جديد ساختيم وارد اون بشيم 
#به عنوان مثال خواهيم داشت 
# current_level
#       ↓
#    Document
#تبديل ميشود به اين 
# Document
#     │
#     └── Science
#             ↑
#       current_level




# -----------------------------------------
# Add actual semantic node
# -----------------------------------------
#خب بعد از بررسي هاي لازم در مورد tree level 
#و اينكه اين نود بايد كجاي درخت قرار بگيره اونو اونجا قرار ميديم 
#يعني وقتشه كه نود را به tree‌اضافه كنيم 
        semantic_node = {
            "title": node.get(
                "title",
                "",
            ),
            "type": node.get(
                "node_type",
                "unknown",
            ),
            "content": node.get(
                "content",
                "",
            ),
            "metadata": metadata,
            "entities": node.get(
                "entities",
                [],
            ),
            "summary": "",
            "children": [],
        }
# واونو به پايين ترين سطح اضافه ميكنيم
        current_level["children"].append(
            semantic_node
        )

    return tree


def _collect_child_context(node: dict) -> str:
    """
    Build compact context from a node's direct children
    for generating a retrieval-oriented parent summary.
    """

    child_contexts = []

    for child in node.get("children", []):

        title = child.get("title", "")
        summary = child.get("summary", "")
        content = child.get("content", "")

        child_text = summary or content

        if child_text:
            child_contexts.append(
                f"Title: {title}\n"
                f"Information: {child_text}"
            )

    return "\n\n".join(child_contexts)



def add_node_summaries(
    node: dict,
    llm,
) -> dict:

    # -----------------------------------------
    # 1. Process children first
    # -----------------------------------------

    for child in node.get("children", []):
        add_node_summaries(
            child,
            llm,
        )

    # -----------------------------------------
    # 2. Determine summary source
    # -----------------------------------------

    content = node.get(
        "content",
        "",
    ).strip()

    if content:
        summary_source = content

    else:
        summary_source = _collect_child_context(
            node
        )

    # Nothing useful to summarize
    if not summary_source:
        return node

    # -----------------------------------------
    # 3. Generate retrieval-oriented summary
    # -----------------------------------------

    prompt = f"""
You are generating a retrieval-oriented summary
for a node in a hierarchical document tree.

The summary will be used later to decide whether
this node is relevant to a user's query.

Node title:

{node.get("title", "")}

Node type:

{node.get("type", "")}

Node information:

{summary_source}

Create a concise retrieval-oriented summary.

Focus on:

- what information this node contains
- important topics
- important entities
- key concepts
- information useful for deciding whether
  this node is relevant to a query

Rules:

- Do not invent information.
- Preserve the original language.
- Do not add external knowledge.
- Be concise.
- Return ONLY the summary.
"""

    print(
        f">>> Generating summary: "
        f"{node.get('title', 'Untitled')}"
    )

    response = llm.invoke(prompt)

    node["summary"] = (
        response_to_text(response).strip()
    )

    return node
import json

from src.utils.json_utils import parse_llm_json


# روند کار به این صورت است 
# Query
#   ↓
# از Root شروع کن
#   ↓
# ببین کدام Child مرتبط است
#   ↓
# وارد Child مرتبط شو
#   ↓
# دوباره Children آن را بررسی کن
#   ↓
# ...
#   ↓
# به Semantic Leaf برس
#   ↓
# Content آن را Retrieve کن

# پس Retriever قرار نیست جواب سؤال رو تولید کنه.

# فقط میگه:

# کدام اطلاعات document برای این query مرتبط هستند؟

# Retriever
# → پیدا کردن اطلاعات مرتبط

# Generator
# → ساختن جواب از اطلاعات مرتبط
def _build_children_index(node: dict) -> list[dict]:
    """
    Create a compact representation of the direct
    children of a tree node for retrieval.
    """


# _build_children_index() یک representation کوچک از children می‌سازه.

    children_index = []

    for index, child in enumerate(
        node.get("children", [])
    ):
        children_index.append(
            {
                "index": index,
                "title": child.get("title", ""),
                "type": child.get("type", ""),
                "summary": child.get("summary", ""),
            }
        )

    return children_index


def select_relevant_children(
    node: dict,
    query: str,
    llm,
) -> list[dict]:
    """
    Select one or more direct children that may
    contain information relevant to the query.
    """
   

    children = node.get("children", [])

    if not children:
        return []

    children_index = _build_children_index(node)

    children_text = json.dumps(
        children_index,
        indent=2,
        ensure_ascii=False,
    )

    prompt = f"""
You are navigating a hierarchical document tree
to retrieve information relevant to a user's query.

Current node:

Title: {node.get("title", "")}
Type: {node.get("type", "")}

User query:

{query}

Direct children of the current node:

{children_text}

Determine which children may contain information
useful for answering the query.

IMPORTANT:

Multiple children may be relevant.

Select ALL children that are reasonably relevant.

Do not force a selection when none of the children
are relevant.

Return ONLY valid JSON:

{{
    "selected_indexes": [0, 2]
}}

Rules:

- selected_indexes must contain only indexes
  present in the provided children.
- Multiple indexes are allowed.
- Do not select unrelated children.
- If none are relevant, return:
  {{"selected_indexes": []}}
- Return ONLY JSON.
- Do not use Markdown.
"""

    response = llm.invoke(prompt)

    try:
        result = parse_llm_json(response)

    except (json.JSONDecodeError, TypeError, ValueError):

        print(
            f">>> Retrieval JSON parsing failed "
            f"at node: {node.get('title', '')}"
        )

        return []

    selected_indexes = result.get(
        "selected_indexes",
        [],
    )

    selected_children = []

    for index in selected_indexes:

        if (
            isinstance(index, int)
            and 0 <= index < len(children)
        ):
            selected_children.append(
                children[index]
            )

    return selected_children




def retrieve_from_tree(
    tree: dict,
    query: str,
    llm,
    max_depth: int = 10,
) -> list[dict]:
    """
    Traverse a hierarchical document tree and
    retrieve relevant semantic nodes.
    """


 
    # Retrieval ما Recursive است
    # یعنی تقریبا این اتفاق میفته
    # visit(node)

    # آیا semantic leaf است؟
    #     ↓
    # YES → Retrieve it

    # NO
    #     ↓
    # Children را بررسی کن
    #     ↓
    # Relevant children را انتخاب کن
    #     ↓
    # برای هر relevant child:
    #     visit(child)
    # یعنی تابع خودش خودشو صدا میزنه
    # Recursive Tree Traversal
    
    # حالا چطوری میفهمیم که به leaf رسیدیم ؟
#     Node has content?
#        │
#    ┌───┴───┐
#   YES      NO
#    ↓        ↓
# Retrieve   Continue navigation
    
    retrieved_nodes = [] # يك ليست خالي ميسازيم براي retrived node‌ ها
    retrieval_trace = [] #ميخواهيم ثبت كنيم در هر مرحله دقيقا چه اتفاقي مي افتد
    
    def traverse(
        node: dict,
        depth: int,
        path: list[str],
    ) -> None:

        if depth > max_depth:
            return
# بهتره مسیری که به نود های relevent میرسیم رو حفظ کنیم
        current_path = path + [
            node.get("title", "")
        ]
        #############################
        children = node.get(
            "children",
            [],
        )
        ############################
        content = node.get(
            "content",
            "",
        )

        # ----------------------------------
        # Leaf / semantic node
        # ----------------------------------


#خب چطور بفهميم يك node از نوع semantic‌است
#چك ميكنيم اگر content پس semantic node‌است 
#آن را retrive‌ كن و اين branch رو متوقف كن
        if content:

            retrieved_nodes.append(
                {
                    "title": node.get(
                        "title",
                        "",
                    ),
                    "type": node.get(
                        "type",
                        "",
                    ),
                    "content": content,
                    "metadata": node.get(
                        "metadata",
                        {},
                    ),
                    "entities": node.get(
                        "entities",
                        [],
                    ),
                    "summary": node.get(
                        "summary",
                        "",
                    ),
                    "path": current_path,
                }
            )


            retrieval_trace.append({
                "depth": depth,
                "current_node": node.get("title", ""),
                "event": "retrieved",
                "path": current_path,
            })
            return 

        # ----------------------------------
        # No content and no children
        # ----------------------------------

#اگر  content نداشت پس  internal node است
#داخل تابع traversal هستيم كه داره خودشو بازگشتي صدا ميزنه
#پس ميره دوباره صدا بزنه تا كي؟
#if depth > max_depth
# كه اون وقت از اين تابع مياد بيرون
        if not children:
            return

        # ----------------------------------
        # Select relevant branches
        # ----------------------------------
# حالا اينجا به كمك llm مياييم relevent children‌رو انتخاب ميكنيم
        selected_children = (
            select_relevant_children(
                node=node,
                query=query,
                llm=llm,
            )
        )


        retrieval_trace.append({
            "depth": depth,
            "current_node": node.get("title", ""),
            "candidates": [
                child.get("title", "")
                for child in node.get("children", [])
            ],
            "selected": [
                child.get("title", "")
                for child in selected_children
            ],
            "path": current_path,
        })
        # ----------------------------------
        # Traverse selected branches
        # ----------------------------------
# حالا براي هر selected children‌بيا  و 
# recursively traverse(child) رو صدا ميزنيم
        for child in selected_children:

            traverse( 
                node=child,
                depth=depth + 1, #اينجا خواست باشه به ازاي هر فرزند كه عميق تر ميشيم
                                 #يكي به depth‌اضافه ميكنيم تا بتونيم عمق رو كنترل كنيم
                path=current_path,
            )

    traverse(
        # اين چون يك تابع داخلي است زمان اجرا ميشود كه اينجا صداش كنيم
        #traversal‌رو از نود Root شروع ميكنيم
        node=tree,
        depth=0, # براي اينكه depth‌رو كنترل كنيم
        path=[], # براي اينكه path فعلي رو نگه داريم
    )

# در پایان تمام retrieved semantic nodes را return کن.
    return {
    "retrieved_nodes": retrieved_nodes,
    "retrieval_trace": retrieval_trace,
}
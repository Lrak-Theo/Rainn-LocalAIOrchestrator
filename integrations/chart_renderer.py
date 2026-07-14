import io


def render_chart_svg(chart_spec):
    # chart_spec is a Python dict extracted from the AI model's JSON output by render_svg_from_json()
    # in stage_output_handler.py. The model is prompted to produce a JSON chart chart_spec at the
    # graph stage. Expected keys: title, labels/categories, values/data, x_label, y_label, color.
    # Example chart_spec: {"title": "Total Costs", "labels": ["A", "B"], "values": [10, 20]}

    try:
        import matplotlib

        # server mode
        matplotlib.use("Agg") 
       
        # plt
        import matplotlib.pyplot as plt

    except Exception:
        return None
    



    # Case 1: Standard format (already chart-ready)
    # These are generated from the model response which is then wrapped in JSON values for chart function
    title = chart_spec.get("title") or "Chart"

    labels = chart_spec.get("labels") or chart_spec.get("categories") or []  
    values = chart_spec.get("values") or chart_spec.get("data") or []   

    x_label = chart_spec.get("x_label") or ""
    y_label = chart_spec.get("y_label") or "Value"

    

    # Case 2: model returned values as a list of dicts e.g. [{"label": "A", "value": 10}, ...]
    # This happens when the model structures the data as objects rather than parallel arrays.
    if values and isinstance(values[0], dict):
        labels = [v.get("label") or v.get("name") or v.get("x") or "" for v in values]
        values = [v.get("value") or v.get("y") or 0 for v in values]

    if not labels or not values:
        return None



    # Case 3: model returned values as a 2D list e.g. [["A", 5, 10, 15], ["B", 2, 4, 6]]
    # This happens when the model outputs a table-like structure instead of flat arrays.
    # We extract the label (first string in the row) and use the last number as the total.
    if isinstance(values[0], list):

        flat_labels, flat_values = [], []

        for i, row in enumerate(values):
            label = next((x for x in row if isinstance(x, str)), labels[i] if i < len(labels) else str(i + 1))
            nums = [x for x in row if isinstance(x, (int, float))]
            if nums:
                flat_labels.append(label)
                flat_values.append(nums[-1])  # last numeric column is usually the total

        labels, values = flat_labels, flat_values


    # If either list is empty or missing, stop and return none
    if not labels or not values:
        return None


    # Make sure labels and values are the same length
    n = min(len(labels), len(values))
    labels = labels[:n]
    values = values[:n]

    # Convert values to numbers; stop if any value is invalid
    try:
        values = [float(v) for v in values]
    except Exception:
        return None


    # Building the bar chart
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=100)
    ax.bar(range(n), values, color=chart_spec.get("color", "#9D99EF"))  # default purple matches Rainn theme
    ax.set_title(title)
    ax.set_ylabel(y_label)
    if x_label:
        ax.set_xlabel(x_label)
    ax.set_xticks(range(n))
    ax.set_xticklabels(labels, rotation=25, ha="right")
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    fig.tight_layout()

    # Save SVG in memory (no temp file), then return it as text
    # Create a text buffer
    buffer = io.StringIO()

    # write chart into buffer as svg text
    fig.savefig(buffer, format="svg")
    plt.close(fig)

    # This line now contains the svg
    return buffer.getvalue()

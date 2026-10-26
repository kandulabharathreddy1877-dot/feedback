from io import BytesIO

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt


GREEN = "#244f3e"
LIME = "#9dbf6b"
RATING_COLORS = ("#d7e7cf", "#a9c78f", "#839f71", "#668953", GREEN)


def render_chart(chart_type: str, dashboard: dict) -> BytesIO:
    if chart_type == "courses":
        items = dashboard["courses"]
        labels = [item["course_name"] for item in items]
        values = [item["average_rating"] for item in items]
        figure, axis = plt.subplots(figsize=(8, max(3, len(items) * 0.65)))
        positions = range(len(items))
        axis.barh(positions, values, color=GREEN, height=0.55)
        axis.set_yticks(list(positions), labels)
        axis.invert_yaxis()
        axis.set_xlim(0, 5)
        axis.set_xlabel("Average rating (out of 5)")
        axis.set_xticks(range(6))
        axis.grid(axis="x", color="#e8ebe4", linewidth=0.8)
        axis.set_axisbelow(True)
        axis.spines[["top", "right", "left"]].set_visible(False)
        axis.spines["bottom"].set_color("#e8ebe4")
        axis.tick_params(axis="y", length=0, pad=10)
        axis.tick_params(axis="x", colors="#697671")
        axis.set_title("Average rating by course", loc="left", color=GREEN, pad=16)
        figure.tight_layout()
    elif chart_type == "faculty":
        items = dashboard["faculty"]
        labels = [
            f"{item['faculty_name']} — {item['subject']}" for item in items
        ]
        values = [item["average_rating"] for item in items]
        figure, axis = plt.subplots(figsize=(8, max(3, len(items) * 0.65)))
        positions = range(len(items))
        axis.barh(positions, values, color=GREEN, height=0.55)
        axis.set_yticks(list(positions), labels)
        axis.invert_yaxis()
        axis.set_xlim(0, 5)
        axis.set_xlabel("Average rating (out of 5)")
        axis.set_xticks(range(6))
        axis.grid(axis="x", color="#e8ebe4", linewidth=0.8)
        axis.set_axisbelow(True)
        axis.spines[["top", "right", "left"]].set_visible(False)
        axis.spines["bottom"].set_color("#e8ebe4")
        axis.tick_params(axis="y", length=0, pad=10)
        axis.tick_params(axis="x", colors="#697671")
        axis.set_title("Faculty feedback by subject", loc="left", color=GREEN, pad=16)
        figure.tight_layout()
    elif chart_type == "ratings":
        counts = [
            sum(course["distribution"][rating] for course in dashboard["courses"])
            for rating in range(1, 6)
        ]
        figure, axis = plt.subplots(figsize=(7, 3.5))
        bars = axis.bar(range(1, 6), counts, color=RATING_COLORS, width=0.62)
        axis.set_xticks(range(1, 6), [f"{rating} star" for rating in range(1, 6)])
        axis.set_ylabel("Number of ratings")
        axis.grid(axis="y", color="#e8ebe4", linewidth=0.8)
        axis.set_axisbelow(True)
        axis.spines[["top", "right", "left"]].set_visible(False)
        axis.spines["bottom"].set_color("#e8ebe4")
        axis.tick_params(colors="#697671")
        axis.set_title("Rating distribution", loc="left", color=GREEN, pad=16)
        axis.bar_label(bars, padding=4, color="#52605a", fontsize=9)
        figure.tight_layout()
    else:
        raise ValueError("Unknown chart type.")

    output = BytesIO()
    figure.savefig(output, format="png", dpi=150, bbox_inches="tight")
    plt.close(figure)
    output.seek(0)
    return output

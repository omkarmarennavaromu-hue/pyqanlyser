import os
import uuid
import json
from flask import request, jsonify, render_template, current_app

from pdf_utils import extract_text
from ai_utils import extract_mcqs, tag_chapter
from db import init_db, insert_question, get_chapter_stats


def register_routes(app):

    # -----------------------------
    # INIT DATABASE
    # -----------------------------
    with app.app_context():
        init_db()

    # -----------------------------
    # HOME PAGE
    # -----------------------------
    @app.route("/")
    def index():
        return render_template("index.html")

    # -----------------------------
    # ANALYZE PDF ROUTE
    # -----------------------------
    @app.route("/analyze", methods=["POST"])
    def analyze():

        file = request.files.get("pdf")

        if not file or file.filename.strip() == "":
            return jsonify({"error": "No PDF uploaded"}), 400

        if not file.filename.lower().endswith(".pdf"):
            return jsonify({"error": "Only PDF files are allowed"}), 400

        unique_name = f"{uuid.uuid4().hex}.pdf"
        save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], unique_name)

        try:
            # Save file
            file.save(save_path)

            # -----------------------------
            # STEP 1: PDF → TEXT
            # -----------------------------
            raw_text = extract_text(save_path)

            if not raw_text or len(raw_text.strip()) < 50:
                return jsonify({"error": "Failed to extract readable text"}), 422

            # -----------------------------
            # STEP 2: TEXT → MCQs (AI)
            # -----------------------------
            mcqs = extract_mcqs(raw_text)

            # Validate AI output
            if not isinstance(mcqs, list):
                return jsonify({
                    "error": "Invalid AI output format",
                    "debug_sample": str(mcqs)[:300]
                }), 500

            if len(mcqs) == 0:
                return jsonify({"error": "No MCQs detected"}), 422

            tagged_questions = []

            # -----------------------------
            # STEP 3: CHAPTER TAGGING
            # -----------------------------
            for mcq in mcqs:

                question_text = mcq.get("question", "").strip()

                if not question_text:
                    continue

                chapter = tag_chapter(question_text)

                tagged_questions.append({
                    "question": question_text,
                    "options": mcq.get("options", []),
                    "answer": mcq.get("answer", ""),
                    "chapter": chapter
                })

            if len(tagged_questions) == 0:
                return jsonify({"error": "No valid questions extracted"}), 422

            # -----------------------------
            # STEP 4: STORE IN DATABASE
            # -----------------------------
            for q in tagged_questions:
                insert_question({
                    "question": q["question"],
                    "options": json.dumps(q["options"]),
                    "answer": q["answer"],
                    "chapter": q["chapter"]
                })

            # -----------------------------
            # STEP 5: ANALYTICS
            # -----------------------------
            chapter_stats = get_chapter_stats()

            total = sum(row["count"] for row in chapter_stats) or 1

            chapter_weightage = [
                {
                    "chapter": row["chapter"],
                    "count": row["count"],
                    "percentage": round((row["count"] / total) * 100, 1)
                }
                for row in chapter_stats
            ]

            top_topics = sorted(
                chapter_weightage,
                key=lambda x: x["count"],
                reverse=True
            )[:5]

            # -----------------------------
            # RESPONSE
            # -----------------------------
            return jsonify({
                "success": True,
                "total_questions": len(tagged_questions),
                "questions": tagged_questions,
                "chapter_weightage": chapter_weightage,
                "top_topics": top_topics
            })

        except Exception as e:
            return jsonify({
                "error": "Processing failed",
                "details": str(e)
            }), 500

        finally:
            # Safe cleanup
            if os.path.exists(save_path):
                try:
                    os.remove(save_path)
                except:
                    pass

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak, Table as RLTable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import Frame, PageTemplate
from datetime import datetime



class UnifiedStudentPerformanceReport:
    TIME_THRESHOLD = 35
    ACCURACY_THRESHOLD = 1
    CLUSTER_LABELS = {0: 'High Performers', 1: 'Moderate Performers', 2: 'Low Performers'}

    ANSWER_KEY = {
        1: 9, 2: 9, 3: 4, 4: 9, 5: 4,
        6: 'triangle', 7: 'sphere', 8: 'square',
        9: 'cube', 10: 'cone',
        11: 7, 12: 8, 13: 8, 14: 9, 15: 16
    }

    def __init__(self, student_id, student_name, responses, synthetic_data_path):
        self.student_id = student_id
        self.student_name = student_name
        self.responses = responses
        self.synthetic_data = pd.read_csv(synthetic_data_path)
        self.new_student_df = None
        self.combined_data = None
        self.average_performance = None
        self.performance_summary = None
        self.recommendations = []
        self.total_score = 0
        self.max_score = 0
        self.question_type_scores = {}
        self.clustering_successful = False
        self.average_question_type_scores = None
        self.question_type_clusters = None

    # def evaluate_answer(self, question_id, user_answer):
    #     correct_answer = self.ANSWER_KEY.get(question_id)
    #     if isinstance(correct_answer, str):
    #         return 1 if user_answer.strip().lower() == correct_answer.lower() else 0
    #     return 1 if user_answer == correct_answer else 0

    def evaluate_answer(self, question_id, user_answer):
      correct_answer = self.ANSWER_KEY.get(question_id)

      # Handle numeric answers
      try:
          user_answer = float(user_answer)
          correct_answer = float(correct_answer)
          return 1 if user_answer == correct_answer else 0
      except ValueError:
          pass  # If conversion fails, it's not numeric

      # Handle string answers
      return 1 if str(user_answer).strip().lower() == str(correct_answer).strip().lower() else 0

    def process_responses(self):
        new_data = []
        for response in self.responses:
            question_id, time_spent, user_answer = response
            question_type = ['arithmetic', 'geometry', 'number_sequence'][(question_id - 1) // 5]
            accuracy = self.evaluate_answer(question_id, user_answer)
            new_data.append([self.student_id, self.student_name, question_id, question_type, time_spent, accuracy])

        self.new_student_df = pd.DataFrame(new_data, columns=['student_id', 'student_name', 'question_id', 'question_type', 'time_spent', 'accuracy'])

        self.new_student_df['performance_category'] = np.where(
            (self.new_student_df['time_spent'] <= self.TIME_THRESHOLD) & (self.new_student_df['accuracy'] == self.ACCURACY_THRESHOLD),
            'Mastered',
            np.where((self.new_student_df['time_spent'] > self.TIME_THRESHOLD) & (self.new_student_df['accuracy'] == self.ACCURACY_THRESHOLD),
                     'Needs Improvement',
                     'Struggling')
        )

        self.total_score = self.new_student_df['accuracy'].sum()
        self.max_score = len(self.new_student_df)

        self.combined_data = pd.concat([self.synthetic_data, self.new_student_df], ignore_index=True)

        # Calculate scores for each question type
        self.question_type_scores = (
            self.new_student_df.groupby('question_type')['accuracy']
            .sum()
            .to_dict()
        )

    def generate_summary_and_recommendations(self):
        self.performance_summary = self.new_student_df.groupby('question_type').performance_category.value_counts().unstack().fillna(0)
        self.performance_summary['Total'] = self.performance_summary.sum(axis=1)

        for category in ['Mastered', 'Needs Improvement', 'Struggling']:
            if category not in self.performance_summary.columns:
                self.performance_summary[category] = 0
            self.performance_summary[category] = (self.performance_summary[category] / self.performance_summary['Total']) * 100

        self.performance_summary.drop(columns=['Total'], inplace=True)

        for question_type, row in self.performance_summary.iterrows():
            mastered = row.get('Mastered', 0)
            needs_improvement = row.get('Needs Improvement', 0)
            struggling = row.get('Struggling', 0)

            if mastered >= 80:
                self.recommendations.append((question_type, f"For {question_type}, Keep up the good work!"))
            elif needs_improvement > 20:
                self.recommendations.append((question_type, f"For {question_type}, Focus on time management and practice."))
            elif struggling >= 20:
                self.recommendations.append((question_type, f"For {question_type}, Consider reviewing fundamentals and additional practice."))
            else:
                self.recommendations.append((question_type, f"For {question_type}, Keep practicing to maintain skills."))

    def calculate_average_scores_and_cluster(self):
        """
        Calculate average scores per question type and perform clustering.
        """
        # Calculate average scores
        average_scores = self.combined_data.groupby("question_type")["accuracy"].mean() * 5  # Scale to 5-point range
        average_scores = average_scores.reset_index()

        # Perform clustering
        kmeans = KMeans(n_clusters=3, random_state=0)
        clusters = kmeans.fit_predict(average_scores["accuracy"].values.reshape(-1, 1))
        average_scores["cluster"] = clusters

        # Save for report generation
        self.average_question_type_scores = average_scores
        self.question_type_clusters = kmeans

        # Visualize clustered bar chart
        self.visualize_average_scores_with_clusters(average_scores)

    def visualize_average_scores_with_clusters(self, average_scores):
        """
        Visualize average scores per question type with clusters.
        """
        plt.figure(figsize=(10, 6))
        for cluster in np.unique(average_scores["cluster"]):
            cluster_data = average_scores[average_scores["cluster"] == cluster]
            plt.bar(
                cluster_data["question_type"],
                cluster_data["accuracy"],
                label=f"Cluster {cluster + 1}",
            )

        plt.title("Average Student Performance")
        plt.xlabel("Question Type")
        plt.ylabel("Average Score Obtained (Out of 5)")
        plt.ylim(0, 5)
        plt.xticks(rotation=45)
        plt.legend(title="Clusters")
        plt.tight_layout()
        plt.savefig("average_scores_clusters.png")
        plt.close()

    def visualize_time_spent(self):
        plt.figure(figsize=(10, 6))
        for question_type in self.new_student_df['question_type'].unique():
            subset = self.new_student_df[self.new_student_df['question_type'] == question_type]
            plt.bar(subset['question_id'], subset['time_spent'], label=question_type, alpha=0.7)
        plt.xlabel("Question ID")
        plt.ylabel("Time Spent (seconds)")
        plt.title(f"Time Spent on Each Question by {self.student_name}")
        plt.legend(title="Question Type")
        plt.tight_layout()
        plt.savefig("time_spent_plot.png")
        plt.close()


    def generate_report(self):
        self.visualize_time_spent()

        # Add average scores visualization
        self.calculate_average_scores_and_cluster()

        file_name = f"performance_report.pdf"
        doc = SimpleDocTemplate(
            file_name,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        styles = getSampleStyleSheet()

        # Define custom styles with Times-Roman font and bold headings
        styles.add(ParagraphStyle(
            name='TitleStyle',
            parent=styles['Title'],
            fontName='Times-Roman',
            alignment=TA_CENTER,
            fontSize=18,
            spaceAfter=20,
            textColor=colors.black
        ))

        styles.add(ParagraphStyle(
            name='NormalStyle',
            parent=styles['Normal'],
            fontName='Times-Roman',
            fontSize=12,
            leading=15,
            alignment=TA_LEFT
        ))

        styles.add(ParagraphStyle(
            name='SubtitleStyle',
            parent=styles['Heading2'],
            fontName='Times-Roman',
            alignment=TA_LEFT,
            spaceAfter=10,
            spaceBefore=20,
            fontSize=14,
            textColor=colors.black,
            bold=True  # Make subtitles bold
        ))

        styles.add(ParagraphStyle(
            name='BulletStyle',
            parent=styles['Normal'],
            fontName='Times-Roman',
            leftIndent=20,
            bulletIndent=10,
            spaceAfter=5,
            bulletFontName='Times-Roman'
        ))

        elements = []

        # Footer Function with red text
        def footer(canvas, doc):
            canvas.saveState()
            canvas.setFont('Times-Roman', 10)
            
            # Get current date and time
            current_datetime = datetime.now().strftime("%B %d, %Y %I:%M %p")
            
            # Create footer text
            footer_text = f"Generated by AI - {current_datetime}"
            
            # Set the text color to red for "Generated by AI"
            canvas.setFillColor(colors.black)
            canvas.drawCentredString(
                letter[0] / 2.0,
                0.75 * inch,
                footer_text
            )
            canvas.restoreState()

        # Add Page Template with Header and Footer
        frame = Frame(
            doc.leftMargin,
            doc.bottomMargin,
            doc.width,
            doc.height,
            id='normal'
        )
        template = PageTemplate(
            id='header_footer',
            frames=frame,
            onPageEnd=footer
        )
        doc.addPageTemplates([template])

        # Title
        elements.append(Paragraph(
            f"<b>Performance Report</b>",
            styles['TitleStyle']
        ))

        ## Total Score
        elements.append(Paragraph(
            f"<b>Obtained Marks:</b> {self.total_score}",
            styles['NormalStyle']
        ))
        elements.append(Paragraph(
            f"<b>Out of:</b> 15",
            styles['NormalStyle']
        ))
        elements.append(Spacer(1, 12))

        # Scores by Question Type Table
        score_data = [["Question Type", "Score Obtained", "Total Score"]]
        for question_type, score in self.question_type_scores.items():
            score_data.append([
                question_type.capitalize(),
                f"{score}",
                "5"
            ])
        score_data.append(["Overall", f"{self.total_score}", "15"])

        score_table = RLTable(score_data, colWidths=[2*inch, 2*inch, 2*inch])
        score_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4F81BD")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Times-Roman'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#DCE6F1")),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Add grid borders
            ('BORDER', (0, 0), (-1, -1), 1, colors.black)  # Add border around the table
        ]))
        elements.append(Paragraph(
            f"<b>Scores by Question Type:</b>",
            styles['SubtitleStyle']
        ))
        elements.append(Spacer(1, 8))
        elements.append(score_table)
        elements.append(Spacer(1, 12))

        # Recommendations as Bullet Points
        if self.recommendations:
            elements.append(Paragraph(
                f"<b>Recommendations</b>",
                styles['SubtitleStyle']
            ))
            for rec in self.recommendations:
                # Use bullet list format
                elements.append(Paragraph(
                    f"• {rec}",
                    styles['BulletStyle']
                ))
            elements.append(Spacer(1, 12))

        # Graphs Side by Side
        if os.path.exists("time_spent_plot.png") and os.path.exists("average_scores_clusters.png"):
            # Create a table for graphs with proper alignment and sizing
            graph_table_data = [
                [
                    Image("time_spent_plot.png", width=3*inch, height=2*inch),
                    Image("average_scores_clusters.png", width=3*inch, height=2*inch)
                ]
            ]
            graphs_table = RLTable(graph_table_data, colWidths=[3*inch, 3*inch])
            graphs_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                ('BORDER', (0, 0), (-1, -1), 1, colors.black)  # Add border around graph table
            ]))
            
            # Add performance visualizations title
            elements.append(Paragraph(
                f"<b>Performance Visualizations:</b>",
                styles['SubtitleStyle']
            ))
            elements.append(Spacer(1, 12))
            elements.append(graphs_table)
            elements.append(Spacer(1, 12))
            
            # Define custom style for paragraph with Times-Roman font and specific font size
            elements.append(Paragraph(
                "The visualizations provided above offer a detailed overview of your child's performance. "
                "These insights will help you better understand key areas of strength and opportunities for improvement. "
                "Thank you for your attention.",
                ParagraphStyle(
                    name='NormalStyleTimesRoman',
                    fontName='Times-Roman',
                    fontSize=10,  # Adjust the font size as needed
                    leading=15,   # Adjust line spacing as needed
                    alignment=TA_LEFT
                )
            ))

            elements.append(Spacer(1, 12))
        else:
            elements.append(Paragraph(
                "Graphs not found.",
                styles['NormalStyle']
            ))
            elements.append(Spacer(1, 12))


        # Build PDF
        doc.build(elements)

        # Clean up images
        if os.path.exists("time_spent_plot.png"):
            os.remove("time_spent_plot.png")
        if os.path.exists("average_scores_clusters.png"):
            os.remove("average_scores_clusters.png")

        print(f"\nReport generated: {file_name}")





# Example Usage
responses = [(1, 2, '9'), (2, 2, '9'), (3, 3, '4'), (4, 2, '9'), (5, 2, '4'), (6, 3, 'Triangle'), (7, 8, 'Sphere'), 
     (8, 3, 'Square'), (9, 5, 'Cube'), (10, 6, 'Cone'), (11, 6, '8'), (12, 3, '8'), (13, 2, '8'), (14, 2, '9'), (15, 3, '16')]

synthetic_data_path = 'classified_student_data.csv'  # Update the path as needed
student_report = UnifiedStudentPerformanceReport(4, "Hafsaaaa", responses, synthetic_data_path)
student_report.process_responses()
student_report.generate_summary_and_recommendations()
student_report.generate_report()

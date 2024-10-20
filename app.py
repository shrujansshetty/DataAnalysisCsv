import pandas as pd
import os
from flask import Flask, render_template, request, jsonify
import matplotlib
matplotlib.use('Agg')  # Set the backend to Agg
import matplotlib.pyplot as plt
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['STATIC_FOLDER'] = 'static'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit

# Create necessary directories if they don't exist
for folder in [app.config['UPLOAD_FOLDER'], app.config['STATIC_FOLDER']]:
    if not os.path.exists(folder):
        os.makedirs(folder)

df = pd.DataFrame()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and file.filename.endswith('.csv'):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        global df
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(file_path, encoding='ISO-8859-1')
            except Exception as e:
                return jsonify({'error': f'Error reading the CSV file: {str(e)}'}), 400

        if df.empty:
            return jsonify({'error': 'Uploaded CSV file is empty'}), 400

        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col], errors='ignore')
            except ValueError:
                pass

        for col in df.columns:
            try:
                df[col] = pd.to_datetime(df[col], errors='ignore')
            except Exception:
                pass  # Ignore if not a date

        return jsonify({'columns': df.columns.tolist()})
    else:
        return jsonify({'error': 'Only CSV files are allowed'}), 400

@app.route('/get_label_fields', methods=['GET'])
def get_label_fields():
    if df.empty:
        return jsonify({'fields': []})
    return jsonify({'fields': df.columns.tolist()})

@app.route('/analyze', methods=['POST'])
def analyze():
    analysis_type = request.form.get('analysis_type')
    selected_field = request.form.get('fields')
    label_field = request.form.get('labelFields')

    if analysis_type == 'pie':
        if not selected_field:
            return jsonify({'error': 'No field selected for analysis'}), 400
        if label_field and label_field not in df.columns:
            return jsonify({'error': f'Label field {label_field} not found in data'}), 400

    plt.figure(figsize=(10, 6))  # Ensure a new figure is created

    try:
        if analysis_type == 'pie':
            if df[selected_field].dtype == 'object':
                # Count occurrences for non-numeric field
                value_counts = df[selected_field].value_counts()
                value_counts.plot(kind='pie', autopct='%1.1f%%')
                plt.title(f'Counts of Unique Values in {selected_field}')
            else:
                # Aggregate numeric data based on labels
                aggregated_data = df.groupby(label_field)[selected_field].sum()
                aggregated_data.plot(kind='pie', autopct='%1.1f%%')
                plt.title(f'Sum of {selected_field} by {label_field}')

        # Save the plot
        image_path = os.path.join(app.config['STATIC_FOLDER'], 'plot.png')
        plt.savefig(image_path)
        plt.close()  # Close the figure to free memory

        return jsonify({'image_url': '/static/plot.png'})
    except Exception as e:
        return jsonify({'error': f'An error occurred during analysis: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(debug=True)

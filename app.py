from flask import Flask, request, render_template, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import inch
from PIL import Image, ImageDraw, ImageFont
import openai
import requests
from io import BytesIO
import logging

# Initialize the Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'jpg', 'jpeg', 'png', 'gif'}
app.secret_key = 'your_secret_key'

# OpenAI API Key Configuration
openai.api_key = os.getenv('OPENAI_API_KEY')

# Logger setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Create uploads folder if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def allowed_file(filename):
    """Check if the file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def generate_illustration(prompt):
    """Generate an illustration using OpenAI's DALL·E model."""
    try:
        response = openai.Image.create(
            prompt=prompt,
            n=1,
            size="1024x1024"
        )
        if response and 'data' in response:
            return response['data'][0]['url']
    except Exception as e:
        logging.error(f"Error generating illustration: {e}")
        flash("Failed to generate illustration. Please try again later.")
    return None

def add_caption_to_image(image_url, caption):
    """Add a caption to the bottom of an image."""
    try:
        response = requests.get(image_url)
        img = Image.open(BytesIO(response.content))
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()  # Customize with a TTF font if required

        # Add text at the bottom of the image
        text_position = (10, img.size[1] - 30)
        draw.text(text_position, caption, (255, 255, 255), font=font)

        # Save the image with a caption
        captioned_image_path = os.path.join(app.config['UPLOAD_FOLDER'], "captioned_image.png")
        img.save(captioned_image_path)
        return captioned_image_path
    except Exception as e:
        logging.error(f"Error adding caption to image: {e}")
        flash("Failed to add caption to the image.")
        return None

def arrange_panels(panels, layout=(2, 2)):
    """Arrange panels in a customizable grid and save as a PDF."""
    try:
        pdf_file = "output.pdf"
        c = canvas.Canvas(pdf_file, pagesize=(6.875 * inch, 10.438 * inch))  # Comic book size

        panel_width = 6.875 * inch / layout[0]
        panel_height = 10.438 * inch / layout[1]

        for i, url in enumerate(panels):
            row = i // layout[0]
            col = i % layout[0]
            x = col * panel_width
            y = (layout[1] - 1 - row) * panel_height

            response = requests.get(url)
            img = Image.open(BytesIO(response.content))
            img_path = os.path.join(app.config['UPLOAD_FOLDER'], f"panel_{i}.png")
            img.save(img_path)  # Save locally first to load into PDF

            c.drawImage(img_path, x, y, width=panel_width, height=panel_height)
            c.showPage()

        c.save()
        return pdf_file
    except Exception as e:
        logging.error(f"Error arranging panels: {e}")
        flash("Failed to arrange panels into a PDF.")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    """Handle file uploads."""
    if request.method == 'POST':
        uploaded_file = request.files.get('file')  # Single file upload
        if not uploaded_file or uploaded_file.filename == '':
            logging.error("No file received in the upload.")
            flash('No file uploaded')
            return redirect(request.url)

        if uploaded_file and allowed_file(uploaded_file.filename):
            filename = secure_filename(uploaded_file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            logging.info(f"Saving file: {filename}")
            uploaded_file.save(file_path)

            flash('File uploaded successfully')
            return redirect(url_for('input_story'))

        else:
            flash('Invalid file type uploaded')
            return redirect(request.url)

    return render_template('upload.html')

@app.route('/story', methods=['GET', 'POST'])
def input_story():
    """Take user input for the story."""
    if request.method == 'POST':
        story_content = request.form['story']
        # Generate multiple illustrations for different story scenes
        illustration_urls = []
        for scene in story_content.split('\n'):
            illustration_url = generate_illustration(scene)
            if illustration_url:
                illustration_urls.append(illustration_url)

        return render_template('storyboard.html', illustration_urls=illustration_urls)

    return render_template('input_story.html')

@app.route('/arrange', methods=['POST'])
def arrange():
    """Arrange panels into a comic book layout."""
    panels = request.form.getlist('panels')
    layout = request.form.get('layout', '2x2')  # Layout from form input
    caption = request.form.get('caption', '')

    if not panels:
        flash('No panels selected')
        return redirect(url_for('index'))

    if caption:
        # If a caption is provided, add it to the first panel for demonstration
        panels[0] = add_caption_to_image(panels[0], caption)

    layout_tuple = tuple(map(int, layout.split('x')))
    pdf_file = arrange_panels(panels, layout=layout_tuple)
    if pdf_file:
        return send_file(pdf_file, as_attachment=True)
    else:
        flash("Failed to generate PDF.")
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)








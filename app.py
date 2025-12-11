# app.py (full overwrite - added edit route and form)
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import json
import os
import datetime
import hashlib

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Change in production

# Data handling
def load_data():
    if not os.path.exists('data.json'):
        return {"next_id": 1, "evidence": []}
    with open('data.json', 'r') as f:
        return json.load(f)

def save_data(data):
    with open('data.json', 'w') as f:
        json.dump(data, f, indent=4)

# Forms
class IntakeForm(FlaskForm):
    name = StringField('File Name', validators=[DataRequired()])
    hash_value = StringField('Hash Value (SHA-256)', validators=[DataRequired()])
    source_device = StringField('Source Device', validators=[DataRequired()])
    investigator = StringField('Investigator Name', validators=[DataRequired()])
    submit = SubmitField('Submit Evidence')

class TransferForm(FlaskForm):
    to_user = StringField('Transfer To', validators=[DataRequired()])
    notes = StringField('Notes')
    submit = SubmitField('Log Transfer')

class VerifyForm(FlaskForm):
    file = FileField('Upload File for Verification', validators=[DataRequired()])
    submit = SubmitField('Verify Hash')

class EditForm(FlaskForm):
    name = StringField('File Name', validators=[DataRequired()])
    hash_value = StringField('Hash Value (SHA-256)', validators=[DataRequired()])
    source_device = StringField('Source Device', validators=[DataRequired()])
    investigator = StringField('Investigator Name', validators=[DataRequired()])
    notes = StringField('Edit Notes (Required for Audit)', validators=[DataRequired()])
    submit = SubmitField('Update Evidence')

# Routes
@app.route('/')
def index():
    data = load_data()
    return render_template('index.html', evidence=data['evidence'])

@app.route('/intake', methods=['GET', 'POST'])
def intake():
    form = IntakeForm()
    if form.validate_on_submit():
        data = load_data()
        now = datetime.datetime.utcnow().isoformat()
        evidence = {
            'id': data['next_id'],
            'name': form.name.data,
            'hash': form.hash_value.data,
            'source': form.source_device.data,
            'investigator': form.investigator.data,
            'timestamp': now,
            'custody_events': [
                {
                    'from': 'Initial Intake',
                    'to': form.investigator.data,
                    'timestamp': now,
                    'notes': 'Initial evidence submission'
                }
            ]
        }
        data['evidence'].append(evidence)
        data['next_id'] += 1
        save_data(data)
        flash('Evidence added successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('intake.html', form=form)

@app.route('/transfer/<int:id>', methods=['GET', 'POST'])
def transfer(id):
    data = load_data()
    evidence = next((e for e in data['evidence'] if e['id'] == id), None)
    if not evidence:
        flash('Evidence not found!', 'danger')
        return redirect(url_for('index'))
    form = TransferForm()
    if form.validate_on_submit():
        now = datetime.datetime.utcnow().isoformat()
        last_custodian = evidence['custody_events'][-1]['to']
        event = {
            'from': last_custodian,
            'to': form.to_user.data,
            'timestamp': now,
            'notes': form.notes.data or ''
        }
        evidence['custody_events'].append(event)
        save_data(data)
        flash('Transfer logged successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('transfer.html', form=form, evidence=evidence)

@app.route('/verify/<int:id>', methods=['GET', 'POST'])
def verify(id):
    data = load_data()
    evidence = next((e for e in data['evidence'] if e['id'] == id), None)
    if not evidence:
        flash('Evidence not found!', 'danger')
        return redirect(url_for('index'))
    form = VerifyForm()
    verification_result = None
    if form.validate_on_submit():
        file = request.files['file']
        if file:
            content = file.read()
            computed_hash = hashlib.sha256(content).hexdigest()
            if computed_hash == evidence['hash']:
                flash('Hash matches! Integrity verified.', 'success')
            else:
                flash('Hash does not match! Integrity compromised.', 'danger')
    return render_template('verify.html', form=form, evidence=evidence)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    data = load_data()
    evidence = next((e for e in data['evidence'] if e['id'] == id), None)
    if not evidence:
        flash('Evidence not found!', 'danger')
        return redirect(url_for('index'))
    form = EditForm(
        name=evidence['name'],
        hash_value=evidence['hash'],
        source_device=evidence['source'],
        investigator=evidence['investigator']
    )
    if form.validate_on_submit():
        now = datetime.datetime.utcnow().isoformat()
        last_custodian = evidence['custody_events'][-1]['to']
        # Log edit as a special custody event
        event = {
            'from': last_custodian,
            'to': last_custodian,  # Stays with same custodian
            'timestamp': now,
            'notes': f'Edit performed: {form.notes.data}'
        }
        evidence['custody_events'].append(event)
        # Update fields
        evidence['name'] = form.name.data
        evidence['hash'] = form.hash_value.data
        evidence['source'] = form.source_device.data
        evidence['investigator'] = form.investigator.data
        save_data(data)
        flash('Evidence updated successfully! Edit logged in chain-of-custody.', 'success')
        return redirect(url_for('index'))
    return render_template('edit.html', form=form, evidence=evidence)

@app.route('/report/<int:id>')
def report(id):
    data = load_data()
    evidence = next((e for e in data['evidence'] if e['id'] == id), None)
    if not evidence:
        flash('Evidence not found!', 'danger')
        return redirect(url_for('index'))
    return render_template('report.html', evidence=evidence)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True)
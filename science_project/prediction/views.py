import os
from django.conf import settings
from django.views import View
from django.shortcuts import render
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from datetime import datetime
from .forms import UploadData


class PredictionView(View):
    def get(self, request):
        # Initialize the upload form only
        upload_form = UploadData()

        # Initial context when no file has been uploaded
        return render(request, 'prediction/index.html', {
            'upload_form': upload_form,
            'regression_equation': None,
            'correlation': None,
            'error': None,
            'plot_url': None,
            'file_uploaded': False,
        })

    def post(self, request):
        if 'file' in request.FILES:
            return self.handle_upload(request)
        elif request.POST.get('action') == 'predict':
            return self.handle_prediction(request)

        # If no valid action is found
        return render(request, 'prediction/index.html', {
            'regression_equation': None,
            'correlation': None,
            'error': 'Invalid request.',
            'plot_url': None,
            'file_uploaded': False,
        })

    def handle_upload(self, request):
        upload_form = UploadData(request.POST, request.FILES)
        if upload_form.is_valid():
            uploaded_file = request.FILES['file']
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
            os.makedirs(upload_dir, exist_ok=True)

            # Save the uploaded file
            file_path = os.path.join(upload_dir, uploaded_file.name)
            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            file_code = os.path.splitext(uploaded_file.name)[0]

            company_file_path = 'prediction/static/data/DaftarSaham.csv'
            df_companies = pd.read_csv(company_file_path)
            company_info = df_companies[df_companies['Code'] == file_code]

            if company_info.empty:
                return render(request, 'prediction/index.html', {
                    'upload_form': upload_form,
                    'error': f"No matching company found for code: {file_code}",
                    'file_uploaded': False,
                })

            # Ambil nama perusahaan dan informasi tambahan
            company_name = company_info.iloc[0]['Name']

            # Read the CSV file
            df = pd.read_csv(file_path)

            # Check if the necessary columns exist in the CSV
            if 'timestamp' not in df.columns or 'close' not in df.columns:
                return render(request, 'prediction/index.html', {
                    'upload_form': upload_form,
                    'regression_equation': None,
                    'correlation': None,
                    'error': 'CSV file is invalid. Ensure it contains "timestamp" and "close" columns.',
                    'plot_url': None,
                    'file_uploaded': False,
                })

            # Process the CSV data for regression
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            X = (df['timestamp'] - pd.to_datetime('1970-01-01')).dt.days
            y = df['close']

            slope, intercept, r, p, std_err = stats.linregress(X, y)

            # Regression function
            def regression_equation(X):
                return slope * X + intercept

            y_pred = regression_equation(X)

            # Plot the regression
            plt.figure(figsize=(10, 6))
            plt.scatter(df['timestamp'], y, color='blue', label='Data Points')
            plt.plot(df['timestamp'], y_pred,
                     color='red', label='Regression Line')
            plt.title('Linear Regression of Stock Prices')
            plt.xlabel('Date')
            plt.ylabel('Stock Price')
            plt.xticks(rotation=45)
            plt.grid()
            plt.legend()

            plot_path = 'prediction/static/prediction/plot.png'
            plt.savefig(plot_path)
            plt.close()

            # Store the file path and regression parameters in session
            request.session['file_path'] = file_path
            request.session['regression_params'] = {
                'slope': slope, 'intercept': intercept, 'r': r
            }
            request.session['data_range'] = {
                'min_date': df['timestamp'].min().strftime('%Y-%m-%d'),
                'max_date': df['timestamp'].max().strftime('%Y-%m-%d'),
            }
            request.session['company_name'] = company_name

            # Return the results
            return render(request, 'prediction/index.html', {
                'upload_form': UploadData(),
                'regression_equation': f'y = {slope:.4f}x + {intercept:.4f}',
                'correlation': r,
                'error': None,
                'plot_url': '/static/prediction/plot.png',
                'file_uploaded': True,
                'company_name': company_name,
            })

        # If the upload form is not valid
        return render(request, 'prediction/index.html', {
            'upload_form': upload_form,
            'regression_equation': None,
            'correlation': None,
            'error': 'Upload form is not valid. Please check your form input and try again.',
            'plot_url': None,
            'file_uploaded': False,
            'company_name': company_name,
        })

    def handle_prediction(self, request):
        # Retrieve session data
        try:
            file_path = request.session.get('file_path')
            regression_params = request.session.get('regression_params')
            data_range = request.session.get('data_range')
            company_name = request.session.get('company_name')

            if not file_path or not regression_params:
                return render(request, 'prediction/index.html', {
                    'error': 'No previous file upload found. Please upload a file first.',
                    'file_uploaded': False,
                })

            # Read the CSV file
            df = pd.read_csv(file_path)
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            # Get prediction date from form
            prediction_date = request.POST.get('prediction_date')
            prediction_date = pd.to_datetime(prediction_date)

            if prediction_date < pd.to_datetime('1900-01-01') or prediction_date > pd.to_datetime('2100-01-01'):
                return render(request, 'prediction/index.html', {
                    'error': 'Tanggal prediksi tidak valid. Pilih tanggal antara tahun 1900 hingga 2100.',
                    'file_uploaded': True,
                    'plot_url': '/static/prediction/plot.png',
                })

            # Calculate days since epoch for prediction
            days_since_epoch = (
                prediction_date - pd.to_datetime('1970-01-01')).days

            # Calculate the predicted value
            slope = regression_params['slope']
            intercept = regression_params['intercept']
            predicted_price = slope * days_since_epoch + intercept

            

            return render(request, 'prediction/index.html', {
                'regression_equation': f"y = {slope:.4f}x + {intercept:.4f}",
                'correlation': regression_params['r'],
                'plot_url': '/static/prediction/plot.png',
                'file_uploaded': True,
                'prediction_date': prediction_date.strftime('%Y-%m-%d'),
                'prediction_result': f"{predicted_price:.2f}",
                'company_name': company_name,
            })

        except Exception as e:
            return render(request, 'prediction/index.html', {
                'error': f'Prediction error: {str(e)}',
                'file_uploaded': False,
            })

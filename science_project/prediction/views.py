import os
from django.conf import settings
from django.views import View
from django.shortcuts import render
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from datetime import datetime
from .forms import UploadData
import matplotlib
matplotlib.use('Agg')


class PredictionView(View):
    def get(self, request):
        return render(request, 'prediction/index.html', {
            'upload_form': UploadData(),
            'file_uploaded': False,
            'plot_url': None,
            'error': None,
        })

    def post(self, request):
        if 'file' in request.FILES:
            return self.handle_upload(request)
        elif request.POST.get('action') == 'predict':
            return self.handle_prediction(request)
        else:
            return self.render_error('Invalid request.')

    def handle_upload(self, request):
        upload_form = UploadData(request.POST, request.FILES)
        if not upload_form.is_valid():
            return self.render_error('Invalid upload form.')

        uploaded_file = request.FILES['file']
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, uploaded_file.name)

        with open(file_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        try:
            # Proses data saham
            company_file_path = 'prediction/static/data/DaftarSaham.csv'
            df_companies = pd.read_csv(company_file_path)
            file_code = os.path.splitext(uploaded_file.name)[0]
            company_info = df_companies[df_companies['Code'] == file_code]

            if company_info.empty:
                return self.render_error(f"No matching company found for code: {file_code}")

            company_name = company_info.iloc[0]['Name']

            # Baca file CSV data saham
            df = pd.read_csv(file_path)
            if 'timestamp' not in df.columns or 'close' not in df.columns:
                return self.render_error('CSV must have "timestamp" and "close" columns.')

            # Preprocessing data
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            X = (df['timestamp'] - pd.to_datetime('1970-01-01')).dt.days
            y = df['close']

            # Hitung regresi
            slope, intercept, r, *_ = stats.linregress(X, y)
            y_pred = slope * X + intercept

            # Persamaan regresi
            regression_equation = f'y = {slope:.4f}x + {intercept:.4f}'

            # Plot hasil regresi
            plt.figure(figsize=(10, 6))
            plt.scatter(df['timestamp'], y, label='Data Points')
            plt.plot(df['timestamp'], y_pred, color='red', label='Regression Line')
            plt.legend()
            plt.title(f'Linear Regression: {company_name}')
            plt.xlabel('Date')
            plt.ylabel('Stock Price')
            plt.xticks(rotation=45)
            plt.grid()

            plot_path = 'prediction/static/prediction/plot.png'
            plt.savefig(plot_path)
            plt.close()

            # Simpan data dalam sesi
            request.session['file_path'] = file_path
            request.session['regression_params'] = {'slope': slope, 'intercept': intercept, 'r': r}
            request.session['company_name'] = company_name
            request.session['regression_equation'] = regression_equation

            return render(request, 'prediction/index.html', {
                'upload_form': UploadData(),
                'file_uploaded': True,
                'plot_url': '/static/prediction/plot.png',
                'correlation': r,
                'regression_equation': regression_equation,
                'company_name': company_name,
            })
        except Exception as e:
            return self.render_error(f'Error processing file: {str(e)}')

    def handle_prediction(self, request):
        try:
            regression_params = request.session.get('regression_params')
            company_name = request.session.get('company_name')
            regression_equation = request.session.get('regression_equation')

            if not regression_params or not company_name:
                return self.render_error('No uploaded file found.')

            prediction_date = pd.to_datetime(request.POST.get('prediction_date'))
            days_since_epoch = (prediction_date - pd.to_datetime('1970-01-01')).days
            slope = regression_params['slope']
            intercept = regression_params['intercept']
            predicted_price = slope * days_since_epoch + intercept

            return render(request, 'prediction/index.html', {
                'file_uploaded': True,
                'plot_url': '/static/prediction/plot.png',
                'correlation': regression_params['r'],
                'prediction_date': prediction_date.strftime('%Y-%m-%d'),
                'prediction_result': f"{predicted_price:.2f}",
                'company_name': company_name,
                'regression_equation': regression_equation,
            })
        except Exception as e:
            return self.render_error(f'Prediction error: {str(e)}')

    def render_error(self, message):
        return render(self.request, 'prediction/index.html', {
            'upload_form': UploadData(),
            'error': message,
            'file_uploaded': False,
            'plot_url': None,
        })

# app/services/chat_data_service.py

def generate_chart_data(data, chart_type):

    if not data:
        return None

    return {
        "chart_type": chart_type,
        "data": data[:20]
    }
import requests
import datetime

from api.services import endpoints
from api.services import static

from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view

@api_view(['POST'])
def lookup(request):
    pega_id = request.data['pega_id']
    response = requests.get("{}{}".format(endpoints.pega_information_api, pega_id))
    data = response.json()

    return Response(data, status=status.HTTP_200_OK)

@api_view(['POST'])
def rent_history(request):
    pega_id = request.data['pega_id']
    response = requests.get("{}{}".format(endpoints.pega_rent_history_api, pega_id))
    data = response.json()['history']

    pay_rent = 0
    share_profit = 0
    history = list()

    for rent in data:
        if rent['rentMode'] == 'PAY_RENT_FEE':
            pay_rent = int(rent['price']) // 1000000000000000000

            history.append({
                'renter_address': rent['renter']['address'],
                'rent_percentage':  'PAY RENT FEE - {} PGX'.format(pay_rent)
            })

        if rent['rentMode'] == 'SHARE_PROFIT':
            share_profit = int(rent['price']) // 10000

            history.append({
                'renter_address': rent['renter']['address'],
                'rent_percentage':  'SHARE PROFIT - {}%'.format(share_profit)
            })

    return Response(history, status=status.HTTP_200_OK)

def _profit_helper(vis_helper, pega_data, rent_data):
    profit_value = 'NO SERVICE'

    share_profit = 0
    pay_rent = 0

    in_service = pega_data['pega']['inService']

    for_owner = 0
    for_scholar = 0

    service = 'NO SERVICE'
    #   0xAA431ECd1254b5AdD1FA48F26CF03EddDb0A6a3f

    for rent in rent_data:
        if rent['rentMode'] == 'PAY_RENT_FEE':
            pay_rent = int(rent['price']) // 1000000000000000000
            service = 'PAY RENT FEE - {} PGX'.format(pay_rent)

        if rent['rentMode'] == 'SHARE_PROFIT':
            share_profit = int(rent['price']) // 10000
            service = 'SHARE PROFIT - {}%'.format(share_profit)

    if pay_rent != 0:
        for_scholar = vis_helper['today_vis']
    
    elif share_profit != 0:
        if share_profit < 10:
            get_percentage = float("0.0{}".format(share_profit))
        elif share_profit == 100:
            get_percentage = float(1)
        else:
            get_percentage = float("0.{}".format(share_profit))

        for_scholar = vis_helper['today_vis'] * get_percentage
        for_owner = vis_helper['today_vis'] - for_scholar
    else:
        for_owner = vis_helper['today_vis']


    return {
        'for_owner': for_owner,
        'for_scholar': for_scholar,
        'service': service
    }

def _vis_helper(data):
    gold = 0
    silver = 0
    bronze = 0
    vis = 0

    today_gold = 0
    today_silver = 0
    today_bronze = 0
    today_vis = 0

    for earned in data['data']:
        if earned['position'] == 1:
            gold += 1
        
        if earned['position'] == 2:
            silver += 1

        if earned['position'] == 3:
            bronze += 1

        vis += earned['reward']

    today_datas = data['data'][:40]

    results = list()
    total_races = 0
    for data in today_datas:
        start_race = int(data['race']['start'])

        today = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')
        date_race = datetime.datetime.utcfromtimestamp(start_race).strftime('%Y-%m-%d')

        if today == date_race:
            total_races += 1
            results.append(data)


    for result in results:
        if result['position'] == 1:
            today_gold += 1
        
        if result['position'] == 2:
            today_silver += 1

        if result['position'] == 3:
            today_bronze += 1

        today_vis += result['reward']

    return {
        'gold': gold,
        'silver': silver,
        'bronze': bronze,
        'vis': vis,
        'today_gold': today_gold,
        'today_silver': today_silver,
        'today_bronze': today_bronze,
        'today_vis': today_vis,
        'total_races': total_races
    }

@api_view(['POST'])
def manage_asset(request):
    address = request.data['address']

    response = requests.get(endpoints.polygon_api.format(str(address)))
    data = response.json()

    token_ids = list()

    for result in data['result']:
        if result['tokenName'] == 'Pegaxy|Pega' and result['tokenSymbol'] == 'PGX-Pega':
            token_id = result['tokenID']
            
            if token_id not in token_ids:
                token_ids.append(token_id)

    assets = list()

    for token in token_ids:
        request = requests.get("{}{}".format(endpoints.pega_information_api, token))
        data = request.json()
        
        if data['pega']['owner']['address'] == address:

            request_history = requests.get("{}{}".format(endpoints.pega_race_history_api, data['pega']['id']))
            history_data = request_history.json()

            vis_helper = _vis_helper(history_data)

            today_gold = vis_helper['today_gold']
            today_silver = vis_helper['today_silver']
            today_bronze = vis_helper['today_bronze']
            today_vis = vis_helper['today_vis']
            total_races = vis_helper['total_races']

            win = today_gold + today_silver + today_bronze
            lose = total_races - win

            pega_data = data

            rent_history = requests.get("{}{}".format(endpoints.pega_rent_history_api, data['pega']['id']))
            rent_data = rent_history.json()['history'][:1]

            profit_helper = _profit_helper(vis_helper, pega_data, rent_data)

            today_owner = profit_helper['for_owner']
            today_renter = profit_helper['for_scholar']
            service = profit_helper['service']

            assets.append({
                'name': data['pega']['name'],
                'energy': data['pega']['energy'],
                'id': data['pega']['id'],
                'gold': today_gold,
                'silver': today_silver,
                'bronze': today_bronze,
                'vis': today_vis,
                'owner': round(today_owner, 2),
                'renter': round(today_renter, 2),
                'service': service,
                'total_races': total_races,
                'win': win,
                'lose': lose
            })

    return Response(assets, status=status.HTTP_200_OK)

@api_view(['POST'])
def vis_chart(request):
    pega_id = request.data['pega_id']
    response = requests.get("{}{}".format(endpoints.pega_race_history_api, pega_id))
    data = response.json()

    today = datetime.datetime.now(datetime.timezone.utc)

    chart = list()
    race_date_history = list()

    gold_list = list()
    silver_list = list()
    bronze_list = list()
    vis_list = list()
    race_list = list()
    
    for day in range(5):
        calculate_date = (today - datetime.timedelta(days=day)).strftime('%Y-%m-%d')
        
        gold = 0
        silver = 0
        bronze = 0
        vis = 0
        total_race = 0

        for race in data['data']:
            start_race = int(race['race']['start'])

            date_race = datetime.datetime.utcfromtimestamp(start_race).strftime('%Y-%m-%d')
            if calculate_date == date_race:
                total_race += 1

                if race['position'] == 1:
                    gold += 1
                
                if race['position'] == 2:
                    silver += 1

                if race['position'] == 3:
                    bronze += 1

                vis += race['reward']
        race_date_history.append(calculate_date)
        
        gold_list.append(gold)
        silver_list.append(silver)
        bronze_list.append(bronze)
        vis_list.append(vis)
        race_list.append(total_race)

    labels = ['Gold', 'Silver', 'Bronze', 'VIS', 'Total Race']
    data_list = [gold_list, silver_list, bronze_list, vis_list, race_list]
    background_color = [
        static.gold_background,
        static.silver_background,
        static.bronze_background,
        static.vis_background,
        static.race_background
    ]

    border_color = [
        static.gold_border,
        static.silver_border,
        static.bronze_border,
        static.vis_border,
        static.race_border
    ]

    for count, label in enumerate(labels):
        chart.append({
            'label': label,
            'data': data_list[count],
            'background': background_color[count],
            'border': border_color[count]
        })



    return Response({
        'chart': chart,
        'labels': race_date_history
    }, status=status.HTTP_200_OK)
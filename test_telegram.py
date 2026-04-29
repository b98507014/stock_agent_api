from ai_stock_suggestion import make_suggestion
import traceback

try:
    result = make_suggestion(cash=30000, execute=False)
    if 'telegram_text' in result:
        print('[OK] telegram_text found')
        print('Length:', len(result['telegram_text']))
        print('\n=== Report ===')
        print(result['telegram_text'])
    else:
        print('[ERROR] telegram_text NOT in result')
        print('Keys:', list(result.keys()))
except Exception as e:
    print('[ERROR]:', str(e))
    traceback.print_exc()

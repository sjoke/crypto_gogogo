from backend import API

key = 'U8ZUqC5bIwbVFEubUUHjzt4k0svJUsX2ej2fVYouCbRLt7aisyLCwz5q6CkxQiwl'
secret = 'CIj5gL9aN8qe3DZHkh0fKaH3wNtOxmyA7HKQhf0RWcYZq0PXyG9AMVF6hW9RicbR'

api = API(key, secret)

res = api.query_margin_balance()
print(res)


# BTCUSD_PERP
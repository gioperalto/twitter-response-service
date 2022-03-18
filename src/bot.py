import os, openai, json, random, re, requests
from http.client import responses
from requests_oauthlib import OAuth1Session

def bearer_oauth(r):
    """
    Method required by bearer token authentication.
    """
    bearer_token = os.environ.get("BEARER_TOKEN")
    r.headers["Authorization"] = f"Bearer {bearer_token}"
    r.headers["User-Agent"] = "Azuki Bot"

    return r

def get_mentions():
    twitter_id = os.environ.get("TWITTER_ID") # Kai's ID
    url = f'https://api.twitter.com/2/users/{twitter_id}/mentions'
    response = requests.request("GET", url, auth=bearer_oauth)

    if response.status_code != 200:
        raise Exception(
            "Request returned an error: {} {}".format(
                response.status_code, response.text
            )
        )
    
    return response.json()['data']

def pick_candidates(tweets):
    candidates = []
    replies = open('data/replies.txt', 'r').read().splitlines()

    for tweet in tweets:
        if not (tweet['id'] in replies):
            url = f"https://api.twitter.com/2/tweets/search/recent?tweet.fields=author_id&query=conversation_id:{tweet['id']}"
            response = requests.request("GET", url, auth=bearer_oauth)
            
            if response.status_code != 200:
                raise Exception(
                    "Request returned an error: {} {}".format(
                        response.status_code, response.text
                    ) 
                )
            resp_json = response.json()
            if resp_json['meta']['result_count'] % 2 == 0:
                candidates.append(tweet)

    return candidates

def filter_tweet(tweet):
    tweet = re.sub("@[a-zA-Z0-9]+", "", tweet)
    tweet = re.sub("https://[a-zA-Z0-9\.\/]+", "", tweet)
    tweet = re.sub("http://[a-zA-Z0-9\.\/]+", "", tweet)

    return tweet.strip()

def generate_response(question):
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    personality = open('seeds/personality.txt', 'r').read()

    # Filter out mentions from question
    question = filter_tweet(question)

    response = openai.Completion.create(
        engine="text-davinci-001",
        prompt=f"{personality}\n    \nYou: {question}\nKai:",
        temperature=0.5,
        max_tokens=60,
        top_p=1,
        frequency_penalty=0.5,
        presence_penalty=0
    )

    story = response['choices'][0]['text']
    return story

def create_oath_session():
    twitter_api_key = os.environ.get("TWITTER_API_KEY")
    twitter_api_secret = os.environ.get("TWITTER_API_SECRET")
    oauth_token = os.environ.get("OAUTH_TOKEN")
    oauth_token_secret = os.environ.get("OAUTH_TOKEN_SECRET")

    oauth = OAuth1Session(
        twitter_api_key,
        client_secret=twitter_api_secret,
        resource_owner_key=oauth_token,
        resource_owner_secret=oauth_token_secret,
    )

    return oauth

def tweet_response(oauth, resp, tweet_id):
    payload = { "text": resp, "reply": { "in_reply_to_tweet_id": tweet_id } }

    print('Payload:', payload)

    # Making the request
    response = oauth.post(
        "https://api.twitter.com/2/tweets",
        json=payload,
    )

    if response.status_code != 201:
        raise Exception("Request returned an error: {} {}".format(response.status_code, response.text))

    print("Response code: {}".format(response.status_code))

    # Saving the response as JSON
    json_response = response.json()
    print(json.dumps(json_response, indent=4, sort_keys=True))
    # Write tweet ID to replies file
    open('data/replies.txt', 'a').write(f'{tweet_id}\n')



if __name__ == "__main__":
    oauth = create_oath_session()
    mentions = get_mentions()
    tweet = random.choice(pick_candidates(mentions))
    print('Tweet chosen:', tweet)
    response = generate_response(tweet['text'])
    tweet_response(oauth=oauth, resp=response, tweet_id=tweet['id'])
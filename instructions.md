This is a bare repository

I want to create a dockerised bot that I can deploy on github actions that searches rightmove for rental properties

It should be scheduled to run every 30 minutes 

It should use a bot to notify new listings each time

no listing should be sent twice 

The search paramters should be defiend by a URL which shows search results 

There should be information and a link included in each result

It should be based on docker / docker compose. Local dev should be done through docker 

I should be able to use the dev containers extension

There should be a devcontainers.json. 

The program should be able to accept multiple inputs. 

The input should be a google sheet which contains headers url	site	telegram_chat_ids	max_price_pp	active	description for example this sheet https://docs.google.com/spreadsheets/d/1PVl4iOOuNSwYjAHw1YYOjd9C0LXyH7kcI1ugmXOpp1I/edit?gid=0#gid=0

site should be 'rightmove' or 'openrent' initially just openrent

There is inspuration in the folder /Users/kennyfitzgerald/rightmove-scraper but it no longer works due to the python package breaking due to some change on the rightmove site 

I should be able to easily run the bot locally to test seing the results as they would be sent to telegram. 

IN the github action it should send to the telegram. 

This should be based on python. 

Suggest any flaws in this appraoch. 

tell me how you will store "seen listings"

don't necesarily fix what I have provied as an example if you think there isa better way.


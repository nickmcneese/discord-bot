Discord Bot for a server that allows you to add rating to others in the server! Modeled based on increasing and decreasing stock value.

Each day, your counter resets and you have 50 positive and 50 negative credits
to spend how you would like on other members in the server.

Commands include:

!buy [user] [integer] allows you to increase the rating of user

!sell [user] [integer] allows you to decrease the rating of user

!rating [user] shows the current rating of a user

!currency shows your daily currency remaining

Makes use of mongoDB to store info about the users and also calls a scheduler that updates everyone's currency daily.
Hosted on heroku!

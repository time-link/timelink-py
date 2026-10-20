### CLI Launcher Creation Commands


Clone a single timelink project directory structure to *path*:

    timelink create project [path] 


Clone a timelink multiproject directory structure to *path*:

    timelink create multiproject [path]


**eventually, these commands should also include the webapp in a */web* folder** (perhaps a different repo?).:


### CLI Launcher Startup Commands

Launch a single project (template):

    timelink start project [path] [-p port] [-d database]


Launch multiproject (template):

    timelink start multiproject [path] [-p port]


Launch web interface:

    timelink start web [-p port]


"""Project package initializer.

Ensures PyMySQL is used as MySQLdb so Django can connect to MySQL
without compiling native mysqlclient bindings (more portable on Windows).
"""

try:
	import pymysql  # type: ignore
	pymysql.install_as_MySQLdb()
except Exception:
	# If PyMySQL isn't installed yet, Django startup will still proceed
	# for non-MySQL engines; installation will be handled by requirements.
	pass

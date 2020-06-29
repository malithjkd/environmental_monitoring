<?php

 $servername = 'localhost';
 $username = "root";
 $password = "1234";
 $database = "serverroom";
 $con = mysql_connect($serverroom, $username, $password);

 $hour = 12;
 mysql_select_db($database,$con);
 $sql = "SELECT * from sensordata WHERE sensorId=1 and time >= (NOW() - INTERVAL $hour HOUR)";
 $dbdata = mysql_query($sql);

?>

<html>
  
  <head><title>Server Room En Monitoring system </title>
  <style>
	  body{
		  background-color: lightGreen;		   
		  }
	  h1 {
		  color: white;
		  text-align: center;
		  font-family: verdana;
		  font-size: 200% 
	  }
	  
	  p{
		  font-family: verdana;
		  font-size: 20pxl
		  
		  }
	  
  </style>
  </head>
  <body><h1>SERVER ROOM ENVIROMENT MONITORING SYSTEM</h1>
		 <p></p>	
  </body>
  
  
  <table width = "300" border = "1" cellspacing = "1" align = "center">
		<tr>
		<th>Tempereture value</th>
		<th>Date</th>
		<tr>
		
		<?php
			while($dbdata1 = mysql_fetch_assoc($dbdata))
			{
				
				echo "<tr>";

				echo "<td>".$dbdata1['sensorValue']."</td>";
				echo "<td>".$dbdata1['time']."</td>";
				echo "<tr>";	
			}
		?>
		
	</table>
</html>

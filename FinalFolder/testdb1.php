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
  
  <head>
 <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/1.0.2/Chart.min.js"></script>
<title>Server Room Conditions Monitoring system </title></head>
  <body  onload="displayLineChart();"><h1>Server Room Enviromental Monitoring System</h1>
  <div class="box">
    <canvas id="lineChart" height="450" width="1300"></canvas>
  </div>
	<table width = "600" border = "1" cellspacing = "1" align = "center">
		<tr>
		<th>Sensor No</th>
		<th>Sensor Value</th>
		<th>Date</th>
		<tr>
		
		<?php
			while($dbdata1 = mysql_fetch_assoc($dbdata))
			{
				
				echo "<tr>";
				echo "<td>".$dbdata1['sensorId']."</td>";
				echo "<td>".$dbdata1['sensorValue']."</td>";
				echo "<td>".$dbdata1['time']."</td>";
				echo "<tr>";	
			}
		?>
		
	</table>
<script language="JavaScript"><!--
  function displayLineChart() {
    var data = {
        labels: [
<?php
 $dbdata = mysql_query($sql);
 $i=0;
			while($dbdata2 = mysql_fetch_assoc($dbdata))
			{
				
				echo $i.",";
				$i++;
			}
		?>
],
        datasets: [
            {
                label: "Tempereture",
                fillColor: "rgba(100,100,220,0.2)",
                strokeColor: "rgba(220,220,220,1)",
                pointColor: "rgba(220,220,220,1)",
                pointStrokeColor: "#fff",
                pointHighlightFill: "#fff",
                pointHighlightStroke: "rgba(220,220,220,1)",
                data: [
<?php
 $dbdata = mysql_query($sql);
			while($dbdata1 = mysql_fetch_assoc($dbdata))
			{
				
				echo $dbdata1['sensorValue'].",";
			}
			
		?>
5]
            }
        ]
    };
    var ctx = document.getElementById("lineChart").getContext("2d");
    var options = { };
    var lineChart = new Chart(ctx).Line(data, options);
  }
  --></script>

</body>
</html>



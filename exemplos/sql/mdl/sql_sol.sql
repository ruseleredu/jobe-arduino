SELECT grupo, ROUND(AVG(t),1) FROM leituras WHERE origem='esp32' GROUP BY grupo ORDER BY grupo;

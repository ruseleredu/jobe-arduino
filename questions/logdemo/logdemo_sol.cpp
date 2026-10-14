void mostrarLogs(int LED_PIN) {
  log_v("Log de Verbose: Informacao detalhada/baixa relevancia.");
  log_d("Log de Debug: Informacao para depuracao do sistema.");
  log_i("Log de Info: Sistema inicializado com sucesso no pino GPIO %d.", LED_PIN);
  log_w("Log de Warning: Este e um exemplo de aviso!");
  log_e("Log de Error: Este e um exemplo de erro simulacao!");
}

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    # Alterar o nome para incluir o prefixo 'apps' para consistência
    # com a forma como o Django pode estar descobrindo/nomeando o app
    # quando está em um subdiretório adicionado ao sys.path.
    name = 'apps.accounts' # Reverted to apps.app_label form
    label = 'accounts' # Definir um label explícito pode ajudar o Django

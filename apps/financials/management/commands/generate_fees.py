from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
# Importe seus modelos aqui, ex: Student, Enrollment, Fee, SchoolYear, GradeLevel
# from apps.students.models import Student
# from apps.academics.models import Enrollment, SchoolYear, GradeLevel
# from apps.financials.models import Fee

class Command(BaseCommand):
    help = 'Gera taxas/mensalidades para alunos matriculados para um determinado período.'

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, help='Ano letivo para o qual gerar as taxas (ex: 2024).', required=True)
        parser.add_argument('--month', type=int, help='Mês para o qual gerar as taxas (1-12). Se não especificado, pode gerar para o ano todo ou um conjunto de meses.', required=False)
        parser.add_argument('--due_day', type=int, default=5, help='Dia do mês para o vencimento da taxa (default: 5).')
        parser.add_argument('--description_template', type=str, default='Mensalidade {month_name}/{year}', help='Template para a descrição da taxa.')
        # Adicionar mais argumentos conforme necessário (ex: para valor, ou para um student_id específico)
        parser.add_argument('--amount', type=float, help='Valor da taxa a ser gerada (ex: 500.00). Se não fornecido, pode usar uma lógica interna.', required=False)
        parser.add_argument('--student_id', type=int, help='ID do usuário do aluno específico para gerar a taxa.', required=False)


    def handle(self, *args, **options):
        year = options['year']
        month = options['month']
        due_day = options['due_day']
        description_template = options['description_template']
        # amount_option = options['amount'] # Para usar depois
        # student_id_option = options['student_id'] # Para usar depois

        self.stdout.write(self.style.SUCCESS(f'Iniciando geração de taxas para {month if month else "o ano de"} {year}...'))

        # 1. Obter o SchoolYear ativo ou o especificado
        # try:
        #     school_year_obj = SchoolYear.objects.get(year=year)
        # except SchoolYear.DoesNotExist:
        #     raise CommandError(f'Ano letivo {year} não encontrado.')

        # 2. Obter todos os Enrollments ativos para este SchoolYear
        # active_enrollments_query = Enrollment.objects.filter(
        #     school_class__school_year=school_year_obj,
        #     status=Enrollment.STATUS_ACTIVE
        # ).select_related('student__user', 'school_class__grade_level')

        # if student_id_option:
        #    active_enrollments_query = active_enrollments_query.filter(student__user_id=student_id_option)

        # active_enrollments = active_enrollments_query.all()

        # if not active_enrollments.exists():
        #     self.stdout.write(self.style.WARNING('Nenhuma matrícula ativa encontrada para os critérios especificados.'))
        #     return

        # count_created = 0
        # for enrollment in active_enrollments:
        #     student = enrollment.student
        #     # 3. Determinar valor da mensalidade (lógica complexa)
        #     # fee_amount = amount_option if amount_option is not None else 500.00 # Exemplo
                # Idealmente, buscar de GradeLevel, ou configuração da turma, etc.
                # fee_config = student.school_class.grade_level.fee_config_set.filter(year=school_year_obj).first()
                # if fee_config: fee_amount = fee_config.monthly_fee
                # else: continue # ou um valor padrão

        #     # 4. Determinar meses para gerar (se --month não foi passado, pode ser um loop de 1 a 12)
        #     # months_to_generate = [month] if month else range(1, 13) # Exemplo para gerar do ano todo

        #     # for m in months_to_generate:
        #         # from datetime import date
        #         # import calendar
        #         # try:
        #         #    # Garante que o dia é válido para o mês
        #         #    last_day_of_month = calendar.monthrange(year, m)[1]
        #         #    actual_due_day = min(due_day, last_day_of_month)
        #         #    due_date = date(year, m, actual_due_day)
        #         # except ValueError:
        #         #    self.stderr.write(self.style.ERROR(f'Dia de vencimento {due_day} inválido para {m}/{year}.'))
        #         #    continue

        #         # month_names_pt = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        #         #                   "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        #         # month_name = month_names_pt[m-1]
        #         # current_description = description_template.format(month_name=month_name, year=year, student_name=str(student))

        #         # 5. Verificar se a taxa já existe
        #         # if not Fee.objects.filter(student=student, school_year=school_year_obj, description__iexact=current_description.strip()).exists():
        #             # Fee.objects.create(
        #             #     student=student,
        #             #     school_year=school_year_obj,
        #             #     description=current_description.strip(),
        #             #     due_date=due_date,
        #             #     amount=fee_amount,
        #             #     status=Fee.STATUS_PENDING
        #             # )
        #             # count_created += 1
        #             # self.stdout.write(f'Criada taxa para {student.user.get_full_name()}: {current_description}')
        #         # else:
        #             # self.stdout.write(self.style.NOTICE(f'Taxa já existente para {student.user.get_full_name()}: {current_description}'))

        # self.stdout.write(self.style.SUCCESS(f'{count_created} taxas criadas com sucesso!'))
        self.stdout.write(self.style.SUCCESS(f'Esqueleto do comando generate_fees executado. Lógica de criação de taxas comentada.'))

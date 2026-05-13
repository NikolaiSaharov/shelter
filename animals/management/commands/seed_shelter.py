from django.core.management.base import BaseCommand
from animals.models import AnimalType, Breed, AnimalStatus, AnimalCharacter, Animal

class Command(BaseCommand):
    help = 'Seed demo data for shelter (types, breeds, characters, animals)'

    def handle(self, *args, **options):
        # Сидим в русских статусах (как в текущей БД)
        status_available, _ = AnimalStatus.objects.get_or_create(status_name='Доступен')
        AnimalStatus.objects.get_or_create(status_name='Пристроен')
        AnimalStatus.objects.get_or_create(status_name='На рассмотрении')

        dog, _ = AnimalType.objects.get_or_create(type_name='Dog')
        cat, _ = AnimalType.objects.get_or_create(type_name='Cat')

        labr, _ = Breed.objects.get_or_create(breed_name='Labrador', defaults={'type': dog})
        terrier, _ = Breed.objects.get_or_create(breed_name='Terrier', defaults={'type': dog})
        brit, _ = Breed.objects.get_or_create(breed_name='British Shorthair', defaults={'type': cat})

        calm, _ = AnimalCharacter.objects.get_or_create(character_name='Calm', defaults={'description': 'Спокойный, дружелюбный'})
        active, _ = AnimalCharacter.objects.get_or_create(character_name='Active', defaults={'description': 'Активный, игривый'})

        animals = [
            dict(animal_name='Гаф', age=1, gender='Male', vaccinated=True, breed=labr, status=status_available, character=active, image_path='https://images.unsplash.com/photo-1548199973-03cce0bbc87b?w=800&q=80', animal_weight=12, height=35),
            dict(animal_name='Чеси', age=1, gender='Female', vaccinated=True, breed=terrier, status=status_available, character=calm, image_path='https://images.unsplash.com/photo-1507146426996-ef05306b995a?w=800&q=80', animal_weight=9, height=30),
            dict(animal_name='Муся', age=2, gender='Female', vaccinated=False, breed=brit, status=status_available, character=calm, image_path='https://images.unsplash.com/photo-1518791841217-8f162f1e1131?w=800&q=80', animal_weight=4, height=20),
        ]

        created = 0
        for data in animals:
            obj, was_created = Animal.objects.get_or_create(
                animal_name=data['animal_name'],
                defaults=dict(
                    age=data['age'], gender=data['gender'], vaccinated=data['vaccinated'],
                    breed=data['breed'], status=data['status'], character=data['character'],
                    image_path=data['image_path'], animal_weight=data['animal_weight'], height=data['height']
                ),
            )
            if was_created:
                created += 1
        self.stdout.write(self.style.SUCCESS(f'Demo data ready. Animals created: {created}'))

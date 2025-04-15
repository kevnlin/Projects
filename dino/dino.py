import pygame
import random
import sys

# Kevin Lin
# My take on the Chrome Dinosaur Game
pygame.init()
if not pygame.font:
    print("Warning: Fonts not initialized!")
    pygame.font.init()

# Game constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 300
GROUND_Y = SCREEN_HEIGHT - 50
GRAVITY = 0.8
JUMP_FORCE = -15
INITIAL_GAME_SPEED = 5
MAX_GAME_SPEED = 15  # 3x the initial speed
SPEED_INCREMENT = 0.001  # How much speed increases per point

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (34, 139, 34)  # Dark green for the dinosaur

try:
    # Set up display
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Dino Runner")
    clock = pygame.time.Clock()
except pygame.error as e:
    print(f"Could not initialize display: {e}")
    sys.exit(1)

class Dino:
    def __init__(self):
        self.x = 50
        self.y = GROUND_Y
        self.width = 40
        self.height = 60
        self.velocity_y = 0
        self.is_jumping = False

    def jump(self):
        if not self.is_jumping:
            self.velocity_y = JUMP_FORCE
            self.is_jumping = True

    def update(self):
        # Apply gravity
        self.velocity_y += GRAVITY
        self.y += self.velocity_y

        # Ground collision
        if self.y > GROUND_Y:
            self.y = GROUND_Y
            self.velocity_y = 0
            self.is_jumping = False

    def draw(self):
        # Body
        pygame.draw.rect(screen, GREEN, (self.x, self.y - self.height, self.width, self.height))
        
        # Head
        head_width = 30
        head_height = 25
        pygame.draw.rect(screen, GREEN, (
            self.x + self.width - 10,
            self.y - self.height - head_height + 10,
            head_width,
            head_height
        ))
        
        # Eye
        pygame.draw.circle(screen, BLACK, (
            int(self.x + self.width + 12),
            int(self.y - self.height - head_height + 22)
        ), 3)
        
        # Leg
        leg_width = 15
        leg_height = 20
        pygame.draw.rect(screen, GREEN, (
            self.x + 10,
            self.y - leg_height,
            leg_width,
            leg_height
        ))

class Cactus:
    def __init__(self):
        self.size_type = random.randint(1, 3)
        
        if self.size_type == 1:  # Small
            self.width = 20
            self.height = 40
        elif self.size_type == 2:  # Medium
            self.width = 30
            self.height = 60
        else:  # Large
            self.width = 35
            self.height = 70
            
        self.x = SCREEN_WIDTH
        self.y = GROUND_Y
        self.speed = INITIAL_GAME_SPEED

    def update(self):
        self.x -= self.speed

    def draw(self):
        # Draw main body
        pygame.draw.rect(screen, BLACK, (self.x, self.y - self.height, self.width, self.height))
        
        # Add some detail based on size
        if self.size_type >= 2:  # Medium and large cacti get side spikes
            spike_width = 10
            # Left spike
            pygame.draw.rect(screen, BLACK, (
                self.x - spike_width/2,
                self.y - self.height * 0.7,
                spike_width,
                self.height * 0.2
            ))
            # Right spike
            pygame.draw.rect(screen, BLACK, (
                self.x + self.width - spike_width/2,
                self.y - self.height * 0.6,
                spike_width,
                self.height * 0.2
            ))

    def off_screen(self):
        return self.x < -self.width

def show_game_over(screen, score):
    font = pygame.font.Font(None, 48)
    game_over_text = font.render("Game Over!", True, BLACK)
    score_text = font.render(f"Final Score: {score}", True, BLACK)
    replay_text = font.render("Press SPACE to replay", True, BLACK)
    
    screen.blit(game_over_text, (
        SCREEN_WIDTH//2 - game_over_text.get_width()//2,
        SCREEN_HEIGHT//2 - 60
    ))
    screen.blit(score_text, (
        SCREEN_WIDTH//2 - score_text.get_width()//2,
        SCREEN_HEIGHT//2
    ))
    screen.blit(replay_text, (
        SCREEN_WIDTH//2 - replay_text.get_width()//2,
        SCREEN_HEIGHT//2 + 60
    ))
    pygame.display.flip()

def main():
    def reset_game():
        return Dino(), [], 0, INITIAL_GAME_SPEED

    try:
        dino, cacti, score, game_speed = reset_game()
        running = True
        game_active = True

        while running:
            # Event handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_SPACE, pygame.K_UP]:
                        if game_active:
                            dino.jump()
                        else:
                            # Reset the game
                            dino, cacti, score, game_speed = reset_game()
                            game_active = True

            if game_active:
                # Update game speed based on score
                game_speed = min(INITIAL_GAME_SPEED + (score * SPEED_INCREMENT), MAX_GAME_SPEED)

                # Spawn cacti
                if len(cacti) == 0 or cacti[-1].x < SCREEN_WIDTH - 300:
                    if random.random() < 0.02:  # 2% chance each frame
                        new_cactus = Cactus()
                        new_cactus.speed = game_speed
                        cacti.append(new_cactus)

                # Update
                dino.update()
                for cactus in cacti:
                    cactus.update()

                # Remove off-screen cacti
                cacti = [c for c in cacti if not c.off_screen()]

                # Collision detection
                for cactus in cacti:
                    if (dino.x < cactus.x + cactus.width and
                        dino.x + dino.width > cactus.x and
                        dino.y - dino.height < cactus.y and
                        dino.y > cactus.y - cactus.height):
                        game_active = False

                # Draw
                screen.fill(WHITE)
                pygame.draw.line(screen, BLACK, (0, GROUND_Y), (SCREEN_WIDTH, GROUND_Y))
                dino.draw()
                for cactus in cacti:
                    cactus.draw()

                # Display score and speed
                font = pygame.font.Font(None, 36)
                score_text = font.render(f"Score: {score}", True, BLACK)
                screen.blit(score_text, (10, 10))

                speed_multiplier = game_speed / INITIAL_GAME_SPEED
                speed_text = font.render(f"Speed: {speed_multiplier:.1f}x", True, BLACK)
                screen.blit(speed_text, (10, 50))

                pygame.display.flip()
                
                # Update score
                score += 1
            else:
                # Show game over screen
                show_game_over(screen, score)

            clock.tick(60)

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        pygame.quit()

if __name__ == "__main__":
    main()

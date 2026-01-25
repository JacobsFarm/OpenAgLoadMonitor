from collections import deque
from collections import Counter

class WeightStabilizer:
    def __init__(self, min_digits=3):
        # Buffer to store the last 5 readings for stability
        self.history = deque(maxlen=5)
        self.current_display_weight = 0
        self.last_valid_reading = 0
        
        # Config: Minimum number of digits (e.g., 3 means 100+). 
        # Prevents reading '65' when the real number is '605'.
        self.min_digits = min_digits
        
        # Config: Ignore jumps larger than 2000kg (glitch protection)
        self.max_jump_threshold = 2000 

    def process_new_reading(self, raw_value):
        """
        Input: Raw integer from YOLO (or None).
        Output: Stabilized weight for the dashboard.
        """
        # 1. If YOLO sees nothing, keep the old value
        if raw_value is None:
            return self.current_display_weight

        # 2. Check digit count (Filter partial reads like '65' instead of '605')
        if len(str(abs(raw_value))) < self.min_digits:
            return self.current_display_weight

        # 3. Filter unrealistic jumps (unless system just started)
        if self.last_valid_reading > 0 and abs(raw_value - self.last_valid_reading) > self.max_jump_threshold:
            return self.current_display_weight

        # 4. Add to history buffer
        self.history.append(raw_value)
        self.last_valid_reading = raw_value

        # 5. VOTING: Determine the most common value in buffer
        counts = Counter(self.history)
        if counts:
            most_common_value, count = counts.most_common(1)[0]

            # Only update display if 3 out of 5 frames agree
            if count >= 3:
                self.current_display_weight = most_common_value
            
        return self.current_display_weight

# Export instance (Adjust min_digits here if needed)
stabilizer = WeightStabilizer(min_digits=3)
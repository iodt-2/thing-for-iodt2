import { Bell } from 'lucide-react';
import { Button } from '@/components/ui/button';

/**
 * Placeholder Notification Bell Component
 * For TwinScale-Lite - simplified version without actual notifications
 */
export default function NotificationBell() {
    return (
        <Button variant="ghost" size="icon" disabled>
            <Bell className="h-5 w-5" />
        </Button>
    );
}

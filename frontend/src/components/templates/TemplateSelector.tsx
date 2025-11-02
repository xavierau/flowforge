import { FileText, User } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Card } from '@/components/ui/card';
import { templates } from '@/templates';
import { loadTemplateAsProperties } from '@/lib/template-loader';
import { useSchemaStore } from '@/store/schemaStore';

const ICON_MAP: Record<string, any> = {
  FileText,
  User,
};

export function TemplateSelector() {
  const { loadTemplate } = useSchemaStore();

  const handleLoadTemplate = (templateId: string) => {
    const template = templates.find((t) => t.id === templateId);
    if (!template) return;

    if (confirm(`Load "${template.name}" template? This will replace your current schema.`)) {
      const { properties, name } = loadTemplateAsProperties(template);
      loadTemplate(properties, name);
    }
  };

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          Load Template
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>Choose a Template</DialogTitle>
          <DialogDescription>
            Start with a pre-built schema template or create your own from scratch
          </DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-2 gap-4 py-4">
          {templates.map((template) => {
            const Icon = ICON_MAP[template.icon || 'FileText'] || FileText;

            return (
              <Card
                key={template.id}
                className="p-4 cursor-pointer hover:border-primary transition-colors"
                onClick={() => handleLoadTemplate(template.id)}
              >
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-primary/10">
                    <Icon className="h-6 w-6 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold mb-1">{template.name}</h3>
                    <p className="text-sm text-muted-foreground line-clamp-2">
                      {template.description}
                    </p>
                    <div className="mt-2">
                      <span className="text-xs px-2 py-1 bg-secondary rounded-full">
                        {template.category}
                      </span>
                    </div>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      </DialogContent>
    </Dialog>
  );
}

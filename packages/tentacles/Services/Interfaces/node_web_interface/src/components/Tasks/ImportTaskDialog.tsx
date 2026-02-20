import { Upload } from "lucide-react"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

import ImportTask from "./ImportTask"

const ImportTaskDialog = () => {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" className="my-4">
          <Upload className="h-4 w-4" />
          Import Tasks
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Import Tasks from CSV</DialogTitle>
          <DialogDescription>
            Upload a CSV file to import multiple tasks at once. The file must
            contain "name" and "type" columns, and optionally a "content" column.
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          <ImportTask onSuccess={() => setIsOpen(false)} />
        </div>

        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline">Cancel</Button>
          </DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default ImportTaskDialog
